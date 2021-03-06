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
import csv
import Baselines
from Baselines import RandomSystem, MostChangedSystem,\
    MostChangedInIntervalSystem, LatestChangedSystem


'''
Class that runs the simulation
@overlap defines how many agents control each node (lamda for poisson distribution so not all nodes are the same)
@systems is a list of system objects (i.e., algorithms to compare)
'''
class Simulation:
    def __init__(self, graph, numAgents, numColors, systems, overlap = 1, maxIterations = 1000, actionLimit = 3, queryLimit = 5, weightInc = 1.0, setting = "all", numNodesPerCluster,pWithin,pBetween):
        #generate graph structure
        self.graph = graph
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
        self.setting = setting
        self.solved = False #is the CSP problem solved (to terminate simulation)
        self.numIterations = 0 
        self.maxIterations = maxIterations
        self.actionLimit = actionLimit
        self.queryLimit = queryLimit
        self.weightIncOfAction = weightInc
        #create agents objects
        self.agents = []   
        self.clusters = {}
        self.nodeToClusterIndex = {}   
        self.generateClusteredGraph(numAgents, numNodesPerCluster, pWithin, pBetween)          
        #assign nodes to agents
        agentAssignments = self.assignAgents()
#        agentAssignments = {0: [2, 5, 6, 7, 8, 9, 10, 11, 14, 16, 19, 21, 22, 25, 27, 29], 1: [0, 1, 3, 4, 5, 6, 8, 11, 14, 15, 20, 22, 23, 24, 26, 29], 2: [1, 3, 8, 9, 10, 12, 13, 15, 17, 18, 19, 22, 24, 28]}
#        agentAssignments = {0: [0, 1, 3, 5, 6, 7, 16, 18, 19, 20, 22, 23, 25, 26, 28, 29, 33, 36, 38, 39, 41, 43, 45, 46, 47], 1: [7, 9, 10, 11, 12, 13, 15, 16, 20, 21, 22, 24, 27, 28, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 43, 44, 45, 46, 49], 2: [1, 2, 4, 7, 8, 11, 13, 14, 15, 17, 23, 24, 26, 28, 30, 32, 35, 36, 38, 42, 48]}

#        #TODO: revert after testing
#        agentAssignments = {}
#        agentAssignments[0] = [0,4,5,6,8]
#        agentAssignments[1] = [7,8,9]
#        agentAssignments[2] = [1,2,3,4,9]
        print agentAssignments
        self.agentAssignments = agentAssignments

            
        return
    def resetSystems(self, newSystems):
        self.systems = newSystems
    
    def assignAgentsByClusters(self):
                
    def assignAgents(self):
        agentAssignments = {}
        agentIds = []
        for agent in range(self.numAgents):
            agentAssignments[agent] = []
            agentIds.append(agent)
        for i in self.graph.nodes():
            numAgentsControllingNode = np.random.poisson(self.overlap) #draw from distribution
            numAgentsControllingNode = max(1,numAgentsControllingNode) #can't have a node that is not controlled by any agent
            numAgentsControllingNode = min(self.numAgents,numAgentsControllingNode) #can't have more than the number of agents controlling a node 
            assignedAgents = random.sample(agentIds, numAgentsControllingNode)
            for a in assignedAgents:
                agentAssignments[a].append(i)
        
        return agentAssignments
    
    def generateClusteredGraph(self,numClusters,nodesPerCluster,pEdgeIn,pEdgeBet):
        g = nx.Graph()
        totalNodeCount = 0

        for clust in numClusters:
            numNodesInClust = max(np.random.poisson(nodesPerCluster),2)
            clusterNodes = [] #TODO: verify doesn't mess up other lists
            for node in numNodesInClust:
                g.add_node(totalNodeCount)
                clusterNodes.append(totalNodeCount)
                self.nodeToClusterIndex[totalNodeCount]=clust
                totalNodeCount=totalNodeCount+1
            self.clusters[clust] = clusterNodes
        #add edges
        for i in range(totalNodeCount):
            for j in range(i+1,totalNodeCount):
                if  self.nodeToClusterIndex[i]==self.nodeToClusterIndex[j]:
                    if np.random.rand()<pEdgeIn:
                        g.add_edge(i,j)
                else:
                    if np.random.rand()<pEdgeBet:
                        g.add_edge(i, j)
            
    def runSimulation(self, outputFilename, graphName, run = 0):
        #store results
        results = []
        #save initial state to revert for each system
        
        #run each system       
        for system in self.systems:
            initialProblem = copy.deepcopy(self.instance)
            self.agents = [] #reset agents
            for agent,nodes in self.agentAssignments.iteritems():
                newAgent = Agent(agent,nodes,copy.deepcopy(self.graph), self.colors,self.actionLimit, reset = False)
                self.agents.append(newAgent)            
            print 'starting to run algorithm: '+str(system)
            while ((self.solved == False) & (self.numIterations<self.maxIterations)): 
                if self.numIterations > 50:
                    a = 0
                for agent in self.agents: #agents iterate in round robin. #TODO: in future, consider non-uniform session
                    if self.setting == "all":
                        nodesToShare = system.query(agent.id, self.queryLimit) #get nodes info to share with agent. nodesToShare is list of nodes
                    else: #only ranking changes, need to send first rev to consider
                        nodesToShare = system.query(agent.id, self.queryLimit, startRev = agent.lastRevision+1)
                    info = {} #dict holding nodes and their colors (to share with agent)
                    for node in nodesToShare:
                        info[node] = self.instance.getColor(node)
                    agent.updateBelief(info) #update agents knowledge

                    actions = agent.chooseActions(self.numIterations,minActions = 3) #query agent for actions
#                    print actions
                    #send update to system
                    actionObjs = []
                    for node,col in actions:
                        actionObj = Action(agent.id, node, 'sigEdit', col, self.weightIncOfAction, 1.0)
                        actionObjs.append(actionObj)
                    session = Session(agent.id, actionObjs, self.numIterations, nodesToShare)
                    system.update(session) #send info back to system
                    
                    #save status
                    res = {}
                    res['graphName'] = graphName
                    res['algorithm'] = system
                    res['iteration'] = self.numIterations
                    state = self.instance.getGraphState()
                    res['conflicts'] = state['conflicts']
                    res['unknown'] = state['unknown']
                    res['notConflicts'] = state['notConflicts']
                    res['percentColored'] = self.instance.getPercentColored()
                    res['run'] = run
                    results.append(res)
                    #send update to GraphProblem
                    self.instance.updateGraph(actions)
#                    filename = "../graphPlots1/"+str(system)+"_"+str(self.numIterations)
#                    self.instance.drawGraph(filename)
                    
                    #increment num of iterations
                    self.numIterations = self.numIterations + 1
                    
            
            #save results
#            res = Result(system, self.numIterations, self.instance.getGraphState(), self.instance.getPercentColored())
#            results[system] = res
            #revert graph and restart iterations counter
            self.instance = initialProblem
            self.numIterations = 0     
            print 'finished running algorithm: '+str(system)
            
        #save results to file
        with open(outputFilename, 'ab') as csvfile:
            fieldnames = ['graphName', 'algorithm', 'iteration', 'conflicts','unknown','notConflicts','percentColored','run']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
            if run == 0:
                writer.writeheader()
            for res in results:
                writer.writerow(res)
        
          
            
def runGraph9nodes():
    systems = []
    randSys = RandomSystem(setting = "changes")
    mostChanged = MostChangedInIntervalSystem(200)
    mostChangeInt = MostChangedInIntervalSystem(5)
    latestSys = LatestChangedSystem()
#    systems.append(randSys)
#    systems.append(mostChanged)
    mip = Mip()
    systems.append(mip)
#    systems.append(randSys)
#    systems.append(mostChangeInt)
#    systems.append(latestSys)
        
    g = nx.Graph()
    for i in range(10):
        g.add_node(i)
    g.add_edge(0, 1)
    g.add_edge(0, 5)
    g.add_edge(0, 6)
    g.add_edge(0, 7)
    g.add_edge(1, 2)               
    g.add_edge(1, 7)
    g.add_edge(1, 9)
    g.add_edge(2, 3)
    g.add_edge(2, 9)
    g.add_edge(3, 4)
    g.add_edge(3, 7)
    g.add_edge(3, 9)
    g.add_edge(4, 5)
    g.add_edge(4, 6)
    g.add_edge(4, 7)
    g.add_edge(4, 8)
    g.add_edge(5, 6)
    g.add_edge(6, 7)
    g.add_edge(6, 8)
    g.add_edge(7, 8)
    g.add_edge(7, 9)
    
    filename = "../results/testingStuff6.csv"
    graphName = "9graph"
    sim = Simulation(g, 3, 3, systems, overlap = 2, maxIterations = 200, actionLimit = 3, queryLimit = 5, weightInc = 1.0, setting = "changes")
    sim.runSimulation(filename,graphName)      
    
def frange(start,stop, step=1.0):
    while start < stop:
        yield start
        start +=step    
    
if __name__ == '__main__':
#    runGraph9nodes()
#    a = 1/0
#    systems = []
#    randSys = RandomSystem(setting = "changes")
#    mostChanged = MostChangedInIntervalSystem(200) #essentially all revisions...
#    mostChangeInt = MostChangedInIntervalSystem(5)
#    latestSys = LatestChangedSystem()
#    systems.append(randSys)
#    systems.append(mostChanged)
#    mip = Mip()
#    systems.append(mip)
#    systems.append(mostChangeInt)
#    systems.append(latestSys)
    
#    graph = nx.fast_gnp_random_graph(20, 0.6)
##    graph = nx.watts_strogatz_graph(20, 5, 0.7)
#    graphName = 'random_20_06'
#    filename= '../results/'+graphName+"__queryLimit3_agents3_overlap2.csv"
#    for i in range(10):     
#        graphName = graphName+"_"+str(i)
#        sim = Simulation(graph, 3, 3, systems, overlap = 2, maxIterations = 200, actionLimit = 3, queryLimit = 3, weightInc = 1.0)
#        sim.runSimulation(filename,graphName)

#    systems = []
#    randSys = RandomSystem()
#    mostChanged = MostChangedSystem()
#    mostChangeInt = MostChangedInIntervalSystem(5)
#    latestSys = LatestChangedSystem()
#    systems.append(randSys)
#    systems.append(mostChanged)
#    mip = Mip()
#    systems.append(mip)
#    systems.append(mostChangeInt)
#    systems.append(latestSys)
#   
    numNodes = 20
    numAgents = 2
    p = 0.1
    
    for numNodes in range(20,51,5):
        for p in frange(0.05,0.3,0.05):
            graph = nx.fast_gnp_random_graph(numNodes,p)
            graphName = 'random_'+str(numNodes)+"_"+str(p)
            for numAgents in range(2,6):                
                systems = []
                randSys = RandomSystem(setting = "changes")
                mostChanged = MostChangedInIntervalSystem(200) #essentially all revisions...
                mostChangeInt = MostChangedInIntervalSystem(5)
                latestSys = LatestChangedSystem()
                systems.append(randSys)
                systems.append(mostChanged)
                mip = Mip()
                systems.append(mip)
                systems.append(mostChangeInt)
                systems.append(latestSys)                  
                sim = Simulation(graph, numAgents, 3, systems, overlap = 2, maxIterations = 150, actionLimit = 5, queryLimit = 5, weightInc = 1.0, setting = "changes")
                systemsBeforeRun = copy.deepcopy(systems)
                filename= '../results/'+graphName+"onlyBetaMIP_200iter_colored_changes_minAction3__queryLimit5_actionLimit5_agents"+str(numAgents)+"_overlap2.csv"
                for i in range(5):            
                    sim.runSimulation(filename,graphName, run = i)
                    sim.resetSystems(systemsBeforeRun)    

#    graph = nx.fast_gnp_random_graph(20, 0.6)
    print 'done'

    a = 1/0         
    graph = nx.fast_gnp_random_graph(30, 0.1)
#    graph = nx.watts_strogatz_graph(20, 5, 0.7)
    graphName = 'random_30_01'
    filename= '../results/'+graphName+"onlyBetaMIP_150iter_colored_changes_minAction0__queryLimit5_actionLimit3_agents3_overlap2.csv"
    for i in range(5):     
        systems = []
        randSys = RandomSystem(setting = "changes")
        mostChanged = MostChangedInIntervalSystem(200) #essentially all revisions...
        mostChangeInt = MostChangedInIntervalSystem(5)
        latestSys = LatestChangedSystem()
        systems.append(randSys)
#        systems.append(mostChanged)
        mip = Mip()
        systems.append(mip)
#        systems.append(mostChangeInt)
#        systems.append(latestSys)      
        graphName = graphName+"_"+str(i)
        sim = Simulation(graph, 3, 3, systems, overlap = 2, maxIterations = 150, actionLimit = 3, queryLimit = 5, weightInc = 1.0, setting = "changes")
        sim.runSimulation(filename,graphName, run = i)    

#    graph = nx.fast_gnp_random_graph(20, 0.6)
    print 'done'

 
#    return

    graphName = 'watts_strogatz_graph_20_5_05'
    filename= '../results/'+graphName+"__all2_actionMin0_queryLimit5_actionLimit5_agents5_overlap2.csv"
    for i in range(1):  
        systems = []
        randSys = RandomSystem(setting = "all")
        mostChanged = MostChangedInIntervalSystem(200)
        mostChangeInt = MostChangedInIntervalSystem(5)
        latestSys = LatestChangedSystem()
        systems.append(randSys)
        systems.append(mostChanged)
        mip = Mip()
        systems.append(mip)
        systems.append(mostChangeInt)
        systems.append(latestSys)
        graph = nx.watts_strogatz_graph(20, 5, 0.5)   
        graphName = graphName+"_"+str(i)
        sim = Simulation(graph, 5, 3, systems, overlap = 2, maxIterations = 200, actionLimit = 5, queryLimit = 5, weightInc = 1.0, setting = "all")
        sim.runSimulation(filename,graphName)       

    a = 1/0 
   
    systems = []
    randSys = RandomSystem()
    mostChanged = MostChangedSystem()
    mostChangeInt = MostChangedInIntervalSystem(5)
    latestSys = LatestChangedSystem()
    systems.append(randSys)
    systems.append(mostChanged)
    mip = Mip()
    systems.append(mip)
    systems.append(mostChangeInt)
    systems.append(latestSys)
            
    graph = nx.watts_strogatz_graph(30, 7, 0.5)
    graphName = 'watts_strogatz_graph_30_7_05'
    filename= '../results/'+graphName+"__queryLimit3_agents5_overlap2.csv"
    for i in range(10):     
        systems = []
        randSys = RandomSystem()
        mostChanged = MostChangedSystem()
        mostChangeInt = MostChangedInIntervalSystem(5)
        latestSys = LatestChangedSystem()
        systems.append(randSys)
        systems.append(mostChanged)
        mip = Mip()
        systems.append(mip)
        systems.append(mostChangeInt)
        systems.append(latestSys)        
        graphName = graphName+"_"+str(i)
        sim = Simulation(graph, 5, 3, systems, overlap = 2, maxIterations = 200, actionLimit = 3, queryLimit = 3, weightInc = 1.0)
        sim.runSimulation(filename,graphName)    

    systems = []
    randSys = RandomSystem()
    mostChanged = MostChangedSystem()
    mostChangeInt = MostChangedInIntervalSystem(5)
    latestSys = LatestChangedSystem()
    systems.append(randSys)
    systems.append(mostChanged)
    mip = Mip()
    systems.append(mip)
    systems.append(mostChangeInt)
    systems.append(latestSys)
            
    graph = nx.watts_strogatz_graph(40, 7, 0.5)
    graphName = 'watts_strogatz_graph_40_7_05'
    filename= '../results/'+graphName+"__queryLimit3_agents5_overlap2.csv"
    for i in range(10): 
        systems = []
        randSys = RandomSystem()
        mostChanged = MostChangedSystem()
        mostChangeInt = MostChangedInIntervalSystem(5)
        latestSys = LatestChangedSystem()
        systems.append(randSys)
        systems.append(mostChanged)
        mip = Mip()
        systems.append(mip)
        systems.append(mostChangeInt)
        systems.append(latestSys)            
        graphName = graphName+"_"+str(i)
        sim = Simulation(graph, 5, 3, systems, overlap = 2, maxIterations = 200, actionLimit = 3, queryLimit = 3, weightInc = 1.0)
        sim.runSimulation(filename,graphName)  

    systems = []
    randSys = RandomSystem()
    mostChanged = MostChangedSystem()
    mostChangeInt = MostChangedInIntervalSystem(5)
    latestSys = LatestChangedSystem()
    systems.append(randSys)
    systems.append(mostChanged)
    mip = Mip()
    systems.append(mip)
    systems.append(mostChangeInt)
    systems.append(latestSys)
            
    graph = nx.binomial_graph(20, 0.5)
    graphName = 'binomial_20_05'
    filename= '../results/'+graphName+"__queryLimit3_agents5_overlap2.csv"
    for i in range(10):   
        systems = []
        randSys = RandomSystem()
        mostChanged = MostChangedSystem()
        mostChangeInt = MostChangedInIntervalSystem(5)
        latestSys = LatestChangedSystem()
        systems.append(randSys)
        systems.append(mostChanged)
        mip = Mip()
        systems.append(mip)
        systems.append(mostChangeInt)
        systems.append(latestSys)          
        graphName = graphName+"_"+str(i)
        sim = Simulation(graph, 5, 3, systems, overlap = 2, maxIterations = 200, actionLimit = 3, queryLimit = 3, weightInc = 1.0)
        sim.runSimulation(filename,graphName)                           

    systems = []
    randSys = RandomSystem()
    mostChanged = MostChangedSystem()
    mostChangeInt = MostChangedInIntervalSystem(5)
    latestSys = LatestChangedSystem()
    systems.append(randSys)
    systems.append(mostChanged)
    mip = Mip()
    systems.append(mip)
    systems.append(mostChangeInt)
    systems.append(latestSys)
        
    graph = nx.binomial_graph(30, 0.5)
    graphName = 'binomial_30_05'
    filename= '../results/'+graphName+"__queryLimit3_agents5_overlap2.csv"
    for i in range(10):  
        systems = []
        randSys = RandomSystem()
        mostChanged = MostChangedSystem()
        mostChangeInt = MostChangedInIntervalSystem(5)
        latestSys = LatestChangedSystem()
        systems.append(randSys)
        systems.append(mostChanged)
        mip = Mip()
        systems.append(mip)
        systems.append(mostChangeInt)
        systems.append(latestSys)           
        graphName = graphName+"_"+str(i)
        sim = Simulation(graph, 5, 3, systems, overlap = 2, maxIterations = 200, actionLimit = 3, queryLimit = 3, weightInc = 1.0)
        sim.runSimulation(filename,graphName)     
    