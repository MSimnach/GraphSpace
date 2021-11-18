# The following class run the following algorithm approach:
# Take: X1,..,Xn obstervation in our Q quotient space
# Step1: Initialize the principal components
# Step2: Align X2,...,Xn wrt m (save the permutation vector)
# Step3: Compute the Principal Components
# Step4: m= Principal Components at current loop
# repreat step2-4 until m is not changing

from core import Graph
from core import GraphSet
from matcher import Matcher, BK, alignment, GA, ID
from distance import euclidean,hamming,sqeuclidean
from AlignCompute import aligncompute
import numpy as np
import itertools
import copy
import math
from sklearn.decomposition import PCA
from sklearn.preprocessing import scale
import re
import pandas as pd

class gpc_aac(aligncompute):
    
    def __init__(self,graphset,matcher):
        aligncompute.__init__(self,graphset,matcher)
        self.mean=None
        self.distance=sqeuclidean()
    # Command of estimation
    # scale=True, the data are scaled
    # s range on the domain of the geodesic for optimal alignment
    def align_and_est(self,n_comp,scale,s,interval_sample=10):
        # If True scaling is applied to the GraphSet
        self.scale=scale
        self.interval_sample=interval_sample
        # Range for the alignment wrt a geodesic
        self.s_min=s[0]
        self.s_max=s[1]
        self.all_steps={}
        self.all_perm={}
        self.pcas={}
        self.pca_error = {}  # pd.DataFrame(0,index=range(graphset.size()), columns=range(self.nr_iterations))
        self.postalignment_error = {}  # pd.DataFrame(0,index=range(graphset.size()), columns=range(self.nr_iterations))
        self.pcaold_error={}
        self.pca_error_huckerman={}
        # k=100 maximum number of iteration
        for k in range(100):
            # STEP 0: Align wrt an randomly selected observation, Compute the first pca
            if(k==0):
                self.f[0]=list(range(self.aX.n_nodes))
                # PREVIOUS:
                m_1 = self.aX.X[0]
                # Align wrt one of the minimum size random element
                #size_obs = {i: len(self.aX.X[i].adj.keys()) for i in range(self.aX.size())}
                #min_size = min(size_obs.values())
                #id_min_size=[i for i, v in size_obs.items() if v == min_size]
                #m_1=self.aX.X[id_min_size[0]]
                for i in range(1,self.aX.size()):
                    # Align X to Y
                    a=self.matcher.align(self.aX.X[i],m_1)
                    # Permutation of X to go closer to Y
                    self.f[i]=a.f 
                # Compute the first Principal Component in the first step
                self.all_perm[k]=self.f
                E_1=self.est(n_comp,k)
                self.all_steps[k]=E_1[0]
                continue
                #return E1
            
            # STEP 1: Align wrt the first principal component
            self.align_geo(E_1[1].loc[0,:],k)
            # STEP 2: Compute the principal component
            if(k>0):
                self.all_perm[k] = self.f
                E_2=self.est(n_comp,k,E_1[3])
                self.all_steps[k]=E_2[0]
            # STEP 3: Step range is the difference between the eigenvalues
            step_range=distance = math.sqrt(sum([(a - b) ** 2 for a, b in zip(E_2[0], E_1[0])]))

            if(step_range<0.01):
                # IF small enough, I am converging! Save and exit.
                self.e_val=E_2[0]
                self.scores=E_2[2]
                if(n_comp==1):
                    self.e_vec=self.give_me_a_network(E_2[1].loc[0,:],n_a=self.aX.node_attr,e_a=self.aX.edge_attr)
                    self.barycenter_net=self.give_me_a_network(self.barycenter,n_a=self.aX.node_attr,e_a=self.aX.edge_attr)
                else:
                    G_PCA=GraphSet()
                    for n_pca in range(n_comp):
                        G_PCA.add(self.give_me_a_network(E_2[1].loc[n_pca,:],n_a=self.aX.node_attr,e_a=self.aX.edge_attr))
                    self.e_vec=G_PCA
                    self.barycenter_net = self.give_me_a_network(self.barycenter, n_a=self.aX.node_attr,
                                                                 e_a=self.aX.edge_attr)
                self.pca_error=pd.DataFrame.from_dict({iteration:[
                    self.pca_error[observation,iteration] for observation in range(self.aX.size())] for
                    iteration in range(0,k+1)})
                self.pcaold_error = pd.DataFrame.from_dict({iteration: [
                    self.pcaold_error[observation, iteration] for observation in range(self.aX.size())] for
                    iteration in range(1, k+1)})

                self.postalignment_error = pd.DataFrame.from_dict({iteration: [
                    self.postalignment_error[observation, iteration] for observation in range(self.aX.size())] for
                                                                iteration in range(1,k+1)})

                self.pca_error_huckerman = pd.DataFrame.from_dict({iteration: [
                    self.pca_error_huckerman[observation, iteration] for observation in range(self.aX.size())] for
                    iteration in range(1, k + 1)})

                print("Step Range smaller than 0.001")
                return
            else:
                # Go on with the computation: update the new result and restart from step 1.
                del E_1
                E_1=E_2
                del E_2
        self.pca_error = pd.DataFrame.from_dict({iteration: [
            self.pca_error[observation, iteration] for observation in range(self.aX.size())] for
            iteration in range(0, k + 1)})
        self.pcaold_error = pd.DataFrame.from_dict({iteration: [
            self.pcaold_error[observation, iteration] for observation in range(self.aX.size())] for
            iteration in range(1, k + 1)})

        self.postalignment_error = pd.DataFrame.from_dict({iteration: [
            self.postalignment_error[observation, iteration] for observation in range(self.aX.size())] for
            iteration in range(1, k + 1)})

        self.pca_error_huckerman = pd.DataFrame.from_dict({iteration: [
            self.pca_error_huckerman[observation, iteration] for observation in range(self.aX.size())] for
            iteration in range(1, k + 1)})
        print("Maximum number of iteration reached.")

        # Return the result
        if('E_2' in locals()):
            self.e_val=E_2[0]
            self.scores=E_2[2]
            self.barycenter_net = self.give_me_a_network(self.barycenter, n_a=self.aX.node_attr,
                                                         e_a=self.aX.edge_attr)
            if(n_comp==1):
                self.e_vec=self.give_me_a_network(E_2[1].loc[0,:],n_a=self.aX.node_attr,e_a=self.aX.edge_attr)

            else:
                G_PCA=GraphSet()
                for n_pca in range(n_comp):
                    G_PCA.add(self.give_me_a_network(E_2[1].loc[n_pca,:],n_a=self.aX.node_attr,e_a=self.aX.edge_attr))
                self.e_vec=G_PCA
                del G_PCA
            del E_2
        else:
            self.e_val=E_1[0]
            self.scores=E_1[2]
            self.barycenter_net = self.give_me_a_network(self.barycenter, n_a=self.aX.node_attr,
                                                         e_a=self.aX.edge_attr)
            if(n_comp==1):
                self.e_vec=self.give_me_a_network(E_1[1].loc[0,:],n_a=self.aX.node_attr,e_a=self.aX.edge_attr)
            else:
                G_PCA=GraphSet()
                for n_pca in range(n_comp):
                    G_PCA.add(self.give_me_a_network(E_1[1].loc[n_pca,:],n_a=self.aX.node_attr,e_a=self.aX.edge_attr))
                self.e_vec=G_PCA
                del G_PCA
            del E_1
        
        
    # Align wrt a geodesic
    def align_geo(self,geo,k):
        self.f.clear()
        # the alignment wrt a geodesic gamma(t) work in two step:
        # In this application, the geodesic gamma is a network so I need 
        # to transform the vector into a network
        self.aX.get_node_attr()
        self.aX.get_edge_attr()
        geo_net=self.give_me_a_network(geo,n_a=self.aX.node_attr,e_a=self.aX.edge_attr)
        if(self.scale==False):
            barycenter_net=self.give_me_a_network(self.barycenter,n_a=self.aX.node_attr,e_a=self.aX.edge_attr)
        # step 1: every graph for every tilde_t in -T,T
        # Save the alignment for every i for every t_tilde in a dictionary
        for i in range(self.aX.size()):
            ind=0
            f_i_t={}
            d_i_t=[]
            d_i_t_ID=[]
            if(self.scale==True):
                for tilde_t in np.arange(self.s_min,+self.s_max,abs(self.s_max-self.s_min)/self.interval_sample):
                    a=self.matcher.align(self.aX.X[i],geo_net.scale(tilde_t))
                    d_i_t+=[a.dis()]
                    f_i_t[ind]=a.f
                    ind+=1
                    a_id= ID(self.distance).align(self.aX.X[i], geo_net.scale(tilde_t))
                    d_i_t_ID+=[a_id.dis()]
                    del a,a_id
            else:
                for tilde_t in np.arange(self.s_min,+self.s_max,abs(self.s_max-self.s_min)/self.interval_sample):
                    # If the data are not scaled then the pca should be recentered in the mean, but the mean is not
                    # The barycenter is computed at the previous alignment step so the data are aligned wrt
                    # the line passing through the barycenter
                    #G_tilde=self.add(1, barycenter_net, tilde_t, self.add(1, barycenter_net, -1, geo_net, range(barycenter_net.nodes())), range(barycenter_net.nodes()))
                    G_tilde = self.add(1, barycenter_net, tilde_t,
                                       geo_net,
                                       range(barycenter_net.nodes()))
                    a = self.matcher.align(self.aX.X[i], G_tilde)
                    d_i_t += [a.dis()]
                    f_i_t[ind] = a.f
                    ind += 1
                    a_id= ID(self.distance).align(self.aX.X[i], G_tilde)
                    d_i_t_ID+=[a_id.dis()]
                    del a,G_tilde,a_id
            # step 2: find the best t_tilde for every i that minimize the distance
            t=np.argmin(d_i_t)
            self.f[i]=f_i_t[t]
            self.postalignment_error[i, k] = np.min(d_i_t)
            self.pca_error_huckerman[i, k] = np.min(d_i_t_ID)

            del ind,d_i_t,f_i_t
    
    # Est is computing the Covariance Matrix. The covariance matrix is the best choice 
    # because it let you deal with different type of distance on node and edges
    def est(self,n_pca,k,old_pca=None):
        # dimension of the dataset
        N=self.aX.size()
        # Step 1: Create the current permuted dataset
        G_per=GraphSet()
        for i in range(N):
            G=copy.deepcopy(self.aX.X[i])
            G.permute(self.f[i])
            G_per.add(G)
            del(G)

        Mat=G_per.to_matrix_with_attr()

        # Standardizing the features
        if(self.scale==True):
            Mat_scale = pd.DataFrame(scale(Mat),columns = Mat.columns)

        else:
            Mat_scale=Mat
            #self.barycenter=np.mean(Mat_scale)
        pca = PCA(n_components=n_pca)
        scores = pca.fit_transform(Mat_scale)
        vals=pca.explained_variance_ratio_
        vecs=pd.DataFrame(pca.components_,columns=Mat_scale.columns)
        self.pcas[k]=[pca,Mat_scale]
        self.barycenter = pd.Series(pca.mean_,index=Mat_scale.columns)#np.mean(Mat_scale)
        if(k>0):
            # Compute the alignment error
            Mat_along_old = pd.DataFrame(old_pca.inverse_transform(scores), columns=Mat_scale.columns)
            for i in range(N):
                x_along = Mat_along_old.iloc[i, :]
                X_curr_pca = self.give_me_a_network(x_along, n_a=self.aX.node_attr, e_a=self.aX.edge_attr)
                matchID = ID(self.distance)
                a=matchID.align(G_per.X[i], X_curr_pca)
                self.pcaold_error[i, k] = a.dis()
                del(matchID,X_curr_pca,x_along,a)


        # Compute the pca error
        # FIT TRANSFORM THE DATA along the first pca
        Mat_along= pd.DataFrame(pca.inverse_transform(scores),
                                     columns=Mat_scale.columns)
        # PCA error:
        for i in range(N):
            x_along=Mat_along.iloc[i,:]
            X_curr_pca= self.give_me_a_network(x_along, n_a=self.aX.node_attr, e_a=self.aX.edge_attr)
            matchID = ID(self.distance)
            a=matchID.align(G_per.X[i], X_curr_pca)
            self.pca_error[i, k] = a.dis()
            del(matchID,X_curr_pca,x_along,a)
        del Mat,Mat_scale,G_per
        return (vals,vecs,scores,pca)
    
    # add function  is the one used for computing the mean
    def add(self,ax,A,ay,B,f):
        # Adjency Matrix: x, y
        y=B.x
        G=copy.deepcopy(A)
        G.permute(f)
        x=G.x

        # coefficients: ax, ay
        # Links
        adjX=G.adj
        adjY=B.adj
        nY=B.n_nodes
        new={}
        fullset=set(x.keys()).union(set(y.keys()))
        
        for i in range(nY):
            if((i,i) in x and (i,i) in y):
                new[i,i]=self.summ(ax,x[i,i],ay,y[i,i])
            elif((i,i) in x and not (i,i) in y):
                new[i,i]=self.summ(ax,x[i,i],ay,None)
            elif((not (i,i) in x) and (i,i) in y):
                new[i,i]=self.summ(ax,None,ay,y[i,i])
                
            #degree=self.X.degree(i)
            linked_nodes=[]
            if(i in adjX and i in adjY):
                linked_nodes=set(adjX[i]).union(set(adjY[i]))
            else:
                if(i in adjX and not i in adjY):
                    linked_nodes=set(adjX[i])
                if(i in adjY and not i in adjX):
                    linked_nodes=set(adjY[i])
                    
            #for j in range(degree):
            for j in linked_nodes:

                if((not (i,j) in y) and (not (i,j) in x)):
                       continue
                elif((i,j) in y and (i,j) in x):
                    new[i,j]=self.summ(ax,x[i,j],ay,y[i,j])
                elif(not (i,j) in y):
                    #new[fi,fj]=self.summ(ax,x[i,j0],ay,[0]*len(x[i,j0]))
                    new[i,j]=self.summ(ax,x[i,j],ay,None)
                    #if(not x.has_key((i,j0))):
                elif(not (i,j) in x):
                    #new[fi,fj]=self.summ(ax,[0]*len(x[i,j0]),ay,y[fi,fj])
                    new[i,j]=self.summ(ax,None,ay,y[i,j])
        newG=Graph(x=new,s=None,adj=None)
        return newG
    
    # Add at y a linear combination of x y=ax*y + ay*x
    def summ(self,ax,x,ay,y): #ax,ay are scalar, x,y are vectors
        if(x is None and y is None):
            return None
        else:
            if(x is None):
                res=[i * ay for i in y]
                return res # ATTENTION: scalar moltiplication of scalar ay with vector y
            else:
                n=len(x)
                if(y is None):
                    y=np.zeros(n)
                res=[]
                for i in range(n):
                    res+=[ax*x[i]+ay*y[i]]
                return res

    # # component wise distance function: usefull to compute the covariance
    # def dis_componentwise(self,A,B,f):
    #     # Adjency Matrix: x, y
    #     y=B.x
    #     G=copy.deepcopy(A)
    #     G.permute(f)
    #     x=G.x
    #     # coefficients: ax, ay
    #     # Links
    #     adjX=G.adj
    #     adjY=B.adj
    #     nX=A.n_nodes
    #     new={}
    #     fullset=set(x.keys()).union(set(y.keys()))
    #     for i in range(nX):
    #         if((i,i) in x and (i,i) in y):
    #             new[i,i]=[math.sqrt(self.measure.node_dis(x[i,i],y[i,i]))]
    #         elif((i,i) in x and not (i,i) in y):
    #             new[i,i]=[math.sqrt(self.measure.node_dis(x[i,i],[0]))]
    #         elif((not (i,i) in x) and (i,i) in y):
    #             new[i,i]=[math.sqrt(self.measure.node_dis(y[i,i],[0]))]
    #
    #         linked_nodes=[]
    #         if(i in adjX and i in adjY):
    #             linked_nodes=set(adjX[i]).union(set(adjY[i]))
    #         else:
    #             if(i in adjX and not i in adjY):
    #                 linked_nodes=set(adjX[i])
    #             if(i in adjY and not i in adjX):
    #                 linked_nodes=set(adjY[i])
    #
    #         for j in linked_nodes:
    #             # Both edges don't exist in both networks (impossible)
    #             if((not (i,j) in y) and (not (i,j) in x)):
    #                    continue
    #             # Both edges exist in both networks
    #             elif((i,j) in y and (i,j) in x):
    #                 new[i,j]=[math.sqrt(self.measure.edge_dis(x[i,j],y[i,j]))]
    #             elif(not (i,j) in y):
    #                 new[i,j]=[math.sqrt(self.measure.edge_dis(x[i,j],[0]))]
    #             elif(not (i,j) in x):
    #                 new[i,j]=[math.sqrt(self.measure.edge_dis([0],y[i,j]))]
    #     newG=Graph(x=new,y=None,adj=None)
    #     return newG
    
    # geo is a pd Series
    # n_a and e_a are nodes and edges attributes
    def give_me_a_network(self,geo,n_a,e_a):
        # create the name of the nodes and edges
        ind=[re.findall(r'-?\d+\.?\d*', k) for k in geo.axes[0]]
        x_g={}
        # loop to fill the x dictionary to create a graph
        for i in range(len(ind)):
            if(len(ind[i])>2 and int(ind[i][0])==int(ind[i][1]) and not (int(ind[i][0]),int(ind[i][1])) in x_g):
                x_g[int(ind[i][0]),int(ind[i][1])]=[geo.loc[geo.axes[0][i+j]] for j in range(n_a)]
            elif(len(ind[i])>2 and int(ind[i][0])!=int(ind[i][1]) and not (int(ind[i][0]),int(ind[i][1])) in x_g):
                x_g[int(ind[i][0]),int(ind[i][1])]=[geo.loc[geo.axes[0][i+j]] for j in range(e_a)]
            elif(len(ind[i])==2 and not (int(ind[i][0]),int(ind[i][1])) in x_g):
                x_g[int(ind[i][0]),int(ind[i][1])]=[geo.loc[geo.axes[0][i]]]
        
        geo_net=Graph(x=x_g,adj=None,s=None)
        return geo_net

    def give_me_a_graphset(self,mat,n_a,e_a):
        return 0
