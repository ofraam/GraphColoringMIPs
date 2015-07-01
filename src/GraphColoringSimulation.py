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
from Utils import Action
from Utils import Result
from Utils import Session


'''
Class that runs the simulation
@overlap defines how many agents control each node (lamda for poisson distribution so not all nodes are the same)
@systems is a list of system objects (i.e., algorithms to compare)
'''
class Simulation:
    def __init__(self, numAgents, numColors, numNodes, numEdges, systems, overlap = 1, maxIterations = 1000, actionLimit = 3, queryLimit = 5, weightInc = 1.0):
        #generate graph structure
        self.graph = nx.dense_gnm_random_graph(numNodes, numEdges)
        #assign random colors
        for node,data in self.graph.nodes(data = True):
            data['color'] = random.randint(0,numColors-1)
            
        #create graphProblem object
        self.colors = [i for i in xrange(numColors)]
        problemGraph = copy.deepcopy(self.graph)

        self.instance = GraphProblem(problemGraph, self.colors)
        self.numAgents = numAgents
        self.overlap = overlap
        self.systems = systems
        self.solved = False #is the CSP problem solved (to terminate simulation)
        self.numIterations = 0 
        self.maxIterations = maxIterations
        self.actionLimit = actionLimit
        self.queryLimit = queryLimit
        self.weightIncOfAction = weightInc
        #assign nodes to agents
        agentAssignments = self.assignAgents()
        #create agents objects
        self.agents = []
        for agent,nodes in agentAssignments.iteritems():
            newAgent = Agent(agent,nodes,copy.deepcopy(self.graph), self.colors,self.actionLimit)
            self.agents.append(newAgent)
            
        return
        
    def assignAgents(self):
        agentAssignments = {}
        for agent in range(self.numAgents):
            agentAssignments[agent] = []
        
        for i in self.graph.nodes():
            numAgentsControllingNode = np.random.poisson(self.overlap)
            assignedAgents = np.random.choice(self.agents, numAgentsControllingNode)
            for a in assignedAgents:
                agentAssignments[a].append(i)
        
        return agentAssignments
    
    def runSimulation(self):
        #store results
        results = {}
        #save initial state to revert for each system
        initialProblem = copy.deepcopy(self.instance)
        #run each system       
        for system in self.systems:
            while ((self.solved == False) & (self.numIterations<self.maxIterations)): 
                for agent in self.agents: #agents iterate in round robin. #TODO: in future, consider non-uniform session
                    nodesToShare = system.query(agent, self.queryLimit) #get nodes info to share with agent. nodesToShare is list of nodes
                    info = {} #dict holding nodes and their colors (to share with agent)
                    for node in nodesToShare:
                        info[node] = self.instance.getColor(node)
                    agent.updateBelief(info) #update agents knowledge
                    actions = agent.chooseActions() #query agent for actions
                    
                    #send update to system
                    actionObjs = []
                    for node,col in actions:
                        actionObj = Action(agent, node, 'sigEdit', col, self.weightIncOfAction, 1.0)
                        actionObjs.append(actionObj)
                    session = Session(agent, actionObjs, self.numIterations)
                    system.update(session) #send info back to system
                    
                    #send update to GraphProblem
                    self.instance.updateGraph(actions)
                    
                    #increment num of iterations
                    self.numIterations = self.numIterations + 1
                    
            
            #save result
            res = Result(system, self.numIterations, self.instance.getGraphState(), self.instance.getPercentColored())
            results[system] = res
            #revert graph and restart iterations counter
            self.instance = initialProblem
            self.numIterations = 0     
          
            
                
    
if __name__ == '__main__':
    sim = Simulation(3,3,20,40,1)
    
    