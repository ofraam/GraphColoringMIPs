'''
Created on Jun 7, 2015

@author: Ofra
'''
import networkx as nx
import math
import numpy as np
import random
from GraphProblem import GraphProblem
from Agent import Agent
import copy
from MIP import Mip

class Simulation:
    def __init__(self, numAgents, numColors, numNodes, numEdges, overlap = 1):
        #generate graph structure
        self.graph = nx.dense_gnm_random_graph(numNodes, numEdges)
        #assign random colors
        for node,data in self.graph.nodes(data = True):
            data['color'] = random.randint(0,numColors-1)
            
        #create graphProblem object
        colors = [i for i in xrange(10)]
        problemGraph = copy.deepcopy(self.graph)

        self.instance = GraphProblem(problemGraph, colors)
        self.numAgents = numAgents
        self.overlap = overlap
        #assign nodes to agents
        agentAssignments = self.assignAgents()
        #create agents objects
        self.agents = []
        for agent,nodes in agentAssignments.iteritems():
            newAgent = Agent(agent,nodes,copy.deepcopy(self.graph))
            self.agents.append(newAgent)
            
        #initialize MIP
        self.mip =  Mip()
        return
        
    def assignAgents(self):
        agentAssignments = {}
        for agent in range(self.numAgents):
            agentAssignments[agent] = []
        
        for i in self.graph.nodes():
            assignedAgents = np.random.choice(self.numAgents, self.overlap)
            for a in assignedAgents:
                agentAssignments[a].append(i)
        
        return agentAssignments
    
    def runSimulation(self,maxIterations = 1000):
        #TODO: actually implement     
        pass  
            
                
    
if __name__ == '__main__':
    sim = Simulation(3,3,20,40,1)
    
    pass