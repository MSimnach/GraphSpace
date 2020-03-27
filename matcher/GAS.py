from core import Graph
from distance import euclidean
from scipy.sparse import lil_matrix,vstack
import numpy as np
import pandas as pd
import math
from matcher import Matcher
from scipy import sparse
import docplex.mp.model as cpx
from sklearn.metrics.pairwise import pairwise_distances

# Docplex brute-force approach

# GAS is a child of matcher
# GAS algorithm is used to compute the match between two network
class GAS(Matcher):

    def __init__(self,X=None,Y=None,f=None):
        Matcher.__init__(self,X,Y,f)
        self.name="Gaaaaaaas!"
        
    
    # The match function: this function find the best match among the equivalent classes
    def match(self,X,Y):
        # Take the two graphs - they have already the same size
        self.X=X
        self.Y=Y
        
        nX=self.X.nodes()
        # nY=self.Y.nodes()
        set_I = range(nX)
        
        # building up the matrix of pairwise distances
        gas = pd.DataFrame(pairwise_distances(X.to_vector_with_attributes().transpose(),
                                              Y.to_vector_with_attributes().transpose() ),
                           columns = Y.to_vector_with_attributes().columns,
                           index = X.to_vector_with_attributes().columns)
        
        # optimization model:
        opt_model = cpx.Model(name="HP Model")
        x_vars  = {(i,u): opt_model.binary_var(name="x_{0}_{1}".format(i,u))
                   for i in set_I for u in set_I}
        
        # constraints
        constraint_sr = {u : opt_model.add_constraint(ct=opt_model.sum(x_vars[i,u] for i in set_I) 
                                                    == 1,ctname="constraint_{0}".format(u)) for u in set_I}

        constraints_cr = {(nX+i) : opt_model.add_constraint(ct=opt_model.sum(x_vars[i,u] for u in set_I) 
                                                    == 1,ctname="constraint_{0}".format(i)) for i in set_I} 
        
        # objective function
        objective = opt_model.sum(x_vars[i,u] * gas.loc['({0}, {0})'.format(i), '({0}, {0})'.format(u)]
                                  for i in set_I 
                                  for u in set_I) + opt_model.sum(x_vars[i,u] * x_vars[j,v] * gas.loc['({0}, {1})'.format(i,j), 
                                                                                                      '({0}, {1})'.format(u,v)]
                                                                  for i in set_I 
                                                                  for u in set_I
                                                                  for j in set_I if j != i
                                                                  for v in set_I if v != u)
        
        opt_model.minimize(objective)
        opt_model.solve()
        
        ff = {k:v.solution_value for k, v in x_vars.items()}
        self.f = [k for (j,k), v in ff.items() if v == 1]
        
 
            

