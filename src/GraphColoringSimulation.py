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
from Baselines import RandomSystem, MostChangedSystem, MostChangedInIntervalSystem, LatestChangedSystem


'''
Class that runs the simulation
@overlap defines how many agents control each node (lamda for poisson distribution so not all nodes are the same)
@systems is a list of system objects (i.e., algorithms to compare)
'''
class Simulation:
    def __init__(self, numAgents, numColors, systems,numNodesPerCluster,pWithin,pBetween,outputFile,fromScratch = False, focus = True, probPrimary = 0.8, overlap = 1, maxIterations = 1000, actionLimit = 3, queryLimit = 5, weightInc = 1.0, setting = "all"):

       
        self.numAgents = numAgents
        self.overlap = overlap
        self.systems = systems
        self.setting = setting
        self.solved = False #is the CSP problem solved (to terminate simulation)
        self.numIterations = 0 
        self.maxIterations = maxIterations*numAgents #iterations = rounds in this case
        self.actionLimit = actionLimit
        self.queryLimit = queryLimit
        self.weightIncOfAction = weightInc
        #create agents objects
        self.agents = []   
        self.clusters = {}
        self.nodeToClusterIndex = {}   
        self.pWithin = pWithin
        self.pBetween = pBetween
        self.graph = self.generateClusteredGraph(numAgents, numNodesPerCluster, pWithin, pBetween)  
        self.focus = focus
        self.probPrimay = probPrimary
        self.fromScratch = fromScratch
        self.lastChangedBy = {} #last changed by
        #generate graph structure
        
        #assign random colors
        for node,data in self.graph.nodes(data = True):
            data['color'] = random.randint(0,numColors-1)
            
        #create graphProblem object
        self.colors = [i for i in xrange(numColors)]
        problemGraph = copy.deepcopy(self.graph)
        self.instance = GraphProblem(problemGraph, self.colors,self.fromScratch)                
        #assign nodes to agents
        agentAssignments = self.assignAgentsDistriburtions(self.probPrimay)
#        agentAssignments = {0: [2, 5, 6, 7, 8, 9, 10, 11, 14, 16, 19, 21, 22, 25, 27, 29], 1: [0, 1, 3, 4, 5, 6, 8, 11, 14, 15, 20, 22, 23, 24, 26, 29], 2: [1, 3, 8, 9, 10, 12, 13, 15, 17, 18, 19, 22, 24, 28]}
#        agentAssignments = {0: [0, 1, 3, 5, 6, 7, 16, 18, 19, 20, 22, 23, 25, 26, 28, 29, 33, 36, 38, 39, 41, 43, 45, 46, 47], 1: [7, 9, 10, 11, 12, 13, 15, 16, 20, 21, 22, 24, 27, 28, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 43, 44, 45, 46, 49], 2: [1, 2, 4, 7, 8, 11, 13, 14, 15, 17, 23, 24, 26, 28, 30, 32, 35, 36, 38, 42, 48]}

#        #TODO: revert after testing
#        agentAssignments = {}
#        agentAssignments[0] = [0,4,5,6,8]
#        agentAssignments[1] = [7,8,9]
#        agentAssignments[2] = [1,2,3,4,9]
#        print agentAssignments
        print self.clusters
        self.agentAssignments = agentAssignments
        self.outputFile = outputFile

            
        return
    

    def resetSystems(self, newSystems):
        self.systems = newSystems
        self.lastChangedBy = {}
    
    '''
    assigns each agents with the nodes in one cluster (only those nodes)
    '''
    def assignAgentsToClustersStrict(self):
        agentAssignments = {}
        
        for i in range(self.numAgents):
            agentAssignments[i] = self.clusters[i]
        
        return agentAssignments

    '''
    assigns each agents distribution over nodes: the sum of the probability for nodes in the agent's primary cluster is #primaryProb, the others get 1-primary prob
    '''    
    def assignAgentsDistriburtions(self, primaryProb):
        agentAssignments = {}
        for i in range(self.numAgents):
            agentAssignments[i] = []
            for c in range(len(self.clusters)):
                if c == i:
                    for node in self.clusters[c]:
                        agentAssignments[i].append((node, primaryProb/len(self.clusters[c]))) #even distribution
                else:
                    for node in self.clusters[c]:
                        agentAssignments[i].append((node, ((1-primaryProb)/(len(self.clusters)-1))/len(self.clusters[c]))) #even distribution                    
            
        return agentAssignments

    '''
    random assignment of nodes to agents. Each node has a number of agents assigned to it based on poisson distribution with mean self.overlap
    '''     
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

    '''
    generates a graph with clusters of nodes, where:
    -number of nodes in each cluster is chosen from a poisson distribution with mean nodesPerCluster
    -edges between nodes in the same cluster are added with probability pEdgeIn
    -edges between nodes in different cluster are added with probability pEdgeBet
    '''    
    def generateClusteredGraph(self,numClusters,nodesPerCluster,pEdgeIn,pEdgeBet):
        g = nx.Graph()
        totalNodeCount = 0

        for clust in range(numClusters):
            numNodesInClust = max(np.random.poisson(nodesPerCluster),2)
#            numNodesInClust =nodesPerCluster
            clusterNodes = [] #TODO: verify doesn't mess up other lists
            for node in range(numNodesInClust):
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
        
        self.nextNodeID =  totalNodeCount               
        return g

    def objExists(self,nodeID): 
        if nodeID in self.nodeToClusterIndex.keys():
            nodeCluster = self.nodeToClusterIndex[nodeID]
            if nodeID in self.clusters[nodeCluster]:
                return True
        return False
    
    def connectNewNode(self,nodeID):
        nodeCluster = self.nodeToClusterIndex[nodeID]
        for i in range(self.nextNodeID):
            if ((self.objExists(i)==True) & (i!=nodeID)):
                if  self.nodeToClusterIndex[i]==nodeCluster:
                    if np.random.rand()<self.pWithin:
                        self.instance.graph.add_edge(i,nodeID)
                else:
                    if np.random.rand()<self.pBetween:
                        self.instance.graph.add_edge(i,nodeID)
                
                
            
    '''
    checks what proportion of the shared nodes are neighbors of nodes from the set actionNodes, divides by the total # of opportunities (sharedNodes*actionNodes)
    '''            
    def relevanceMetric(self, actionNodes, sharedNodes):
        relevanceCount = 0.0
        for sharedNode in sharedNodes:
            for actNode in actionNodes:
                if sharedNode in nx.neighbors(self.instance.graph, actNode):
                    relevanceCount = relevanceCount + 1.0
        opportunity= len(sharedNodes)*len(actionNodes)
        if opportunity == 0:
            return 0
        else:
            return relevanceCount/opportunity

    '''
    for each node in shared nodes, check whether it was relevant. returns the proportion of relevant nodes
    '''          
    def relevanceMetricBinaryNodes(self, actionNodes, sharedNodes):
        relevanceCount = 0.0
        for sharedNode in sharedNodes:
            for actNode in actionNodes:
                if sharedNode in nx.neighbors(self.instance.graph, actNode):
                    relevanceCount = relevanceCount + 1.0
                    break;
        opportunity= len(sharedNodes)
        if opportunity == 0:
            return 0
        else:
            return relevanceCount/opportunity        

    '''
    checks what proportion of all relevant nodes were retrieved (shared)
    '''         
    def relevanceRecall(self, actionNodes, sharedNodes):
        relevantNodes = []
        for actNode in actionNodes:
            for neighbor in nx.neighbors(self.instance.graph, actNode):
#                if neighbor not in actionNodes: #not sure this is correct
                relevantNodes.append(neighbor)
                    
        shared = 0.0
        for sharedNode in sharedNodes:
            if sharedNode in relevantNodes:
                shared = shared+1
        if len(relevantNodes)==0:
            print 'nothing'
            return 0
        recall = shared/len(relevantNodes)
        return recall

    '''
    checks what proportion of all relevant nodes were retrieved (shared)
    '''         
    def relevanceRecallChanged(self, actionNodes, sharedNodes, agent, focusObj):
        relevantNodes = []
        for actNode in actionNodes:
            for neighbor in nx.neighbors(self.instance.graph, actNode):
                if neighbor not in relevantNodes:
#                if neighbor not in actionNodes: #not sure this is correct
                    if neighbor in self.lastChangedBy.keys():
                        if self.lastChangedBy[neighbor]!=agent:
                            if neighbor!=focusObj:
                                relevantNodes.append(neighbor)
                        
                    
        shared = 0.0
        for sharedNode in sharedNodes:
            if sharedNode in relevantNodes:
                shared = shared+1
        if len(relevantNodes)==0:
            return 1
        recall = shared/len(relevantNodes)
        return recall    

    '''
    checks how many of the nodes that were shared were relevant 
    '''    
    def relevancePrecision(self, actionNodes, sharedNodes):
        relevantNodes = []
        for actNode in actionNodes:
            for neighbor in nx.neighbors(self.instance.graph, actNode):
#                if neighbor not in actionNodes: #not sure this is correct
                relevantNodes.append(neighbor)
                    
        shared = 0.0
        for sharedNode in sharedNodes:
            if sharedNode in relevantNodes:
                shared = shared+1
        if len(relevantNodes)==0:
            print 'nothing'
            return 0
        prec = shared/self.queryLimit
        return prec    

    def relevancePrecisionChanged(self, actionNodes, sharedNodes,changedBelief):
        relevantNodes = []
        for actNode in actionNodes:
            for neighbor in nx.neighbors(self.instance.graph, actNode):
#                if neighbor not in actionNodes: #not sure this is correct
                relevantNodes.append(neighbor)
                    
        shared = 0.0
        for i in range(len(sharedNodes)):
            if ((sharedNodes[i] in relevantNodes) & (changedBelief[i]==1)):
                shared = shared+1
        if len(relevantNodes)==0:
            print 'nothing'
            return 0
        prec = shared/self.queryLimit
        return prec 
    
    def precisionChangedByOtherAgent(self, actionNodes, sharedNodes, agent):
        relevantNodes = []
        for actNode in actionNodes:
            for neighbor in nx.neighbors(self.instance.graph, actNode):
                relevantNodes.append(neighbor)
#                if neighbor not in actionNodes: #not sure this is correct
#                if neighbor in self.lastChangedBy.keys():
#                    if self.lastChangedBy[neighbor]!=agent:
#                        relevantNodes.append(neighbor)

                    
        shared = 0.0
        for i in range(len(sharedNodes)):
            if sharedNodes[i] in relevantNodes:
                if sharedNodes[i] in self.lastChangedBy.keys():
                    if self.lastChangedBy[sharedNodes[i]]!=agent:
                        shared = shared+1
                    else:
                        print 'here'
        if ((len(relevantNodes)==0) | (len(sharedNodes)==0)):
#            print 'nothing'
            return 0
        prec = shared/len(sharedNodes)
        return prec         
    '''
    a proximity metric: checks what was the distance between each of the shared nodes and the focus node. Returns the reciprocal to avoid inifinity distance when two nodes are not connected
    '''        
    def distanceFromFocusMetric(self, focusNode, sharedNodes):
        totalDist = 0.0
        for node in sharedNodes:
            try:
                totalDist = totalDist + 1.0/(len(nx.shortest_path(self.instance.graph, focusNode, node))-1)
            except:
                totalDist = totalDist
        if len(sharedNodes)>0:
            averageDistance = totalDist/len(sharedNodes)
        else:
            return 0
        return averageDistance
    
    def changedAgentBeliefRatio(self,changedBelief):
        return sum(changedBelief/float(self.queryLimit))
    

    def runSimulationDynamic(self, graphName, run = 0, learnTime = -1):

        #store results
        results = []
        #save initial state to revert for each system
        seed = np.random.randint(2)
        #run each system  
        for system in self.systems:
            initialProblem = copy.deepcopy(self.instance)
            self.agents = [] #reset agents
            
            for agent,nodes in self.agentAssignments.iteritems():
                newAgent = Agent(agent,copy.deepcopy(self.clusters),copy.deepcopy(self.graph), self.colors,self.actionLimit, reset = False, seed = seed, pPrimary = self.probPrimay)
                self.agents.append(newAgent)            
            print 'starting to run algorithm: '+str(system)
            while self.numIterations<self.maxIterations: 
                for agent in self.agents: #agents iterate in round robin. #TODO: in future, consider non-uniform session
                    print '----------agent = '+str(agent.id)+'-----------------'
                    nodesToChange = copy.deepcopy(agent.chooseNodesByDistributionDynamic()) #agent chooses the nodes to change TODO: later possibly inform system of this choice
                    actionTypes = agent.chooseActionTypes() #agent chooses whether to modify/add/remove for each object
                    
                   
                    #query system
                    if self.setting == "all":
                        if self.focus:
                            nodesToShare = system.query(agent.id, self.queryLimit, startRev=0, node = nodesToChange[0]) #get nodes info to share with agent. nodesToShare is list of nodes
                        else:
                            nodesToShare = system.query(agent.id, self.queryLimit, startRev=0, node = None)  
                    
                    else: #only ranking changes, need to send first rev to consider
                        if self.focus:
                            nodesToShare = system.query(agent.id, self.queryLimit, startRev = agent.lastRevision+1, node = nodesToChange[0]) 
                        else:    
                            nodesToShare = system.query(agent.id, self.queryLimit, startRev = agent.lastRevision+1, node = None)
                    print 'nodesToChange: '+str(nodesToChange)
                    print 'nodesToShare: '+str(nodesToShare)
                    #compute metrics
                    print 'graph nodes: '+str(self.instance.graph.nodes())
                    relevance = self.relevanceMetric(nodesToChange, nodesToShare)
                    relevanceBinary = self.relevanceMetricBinaryNodes(nodesToChange, nodesToShare)
                    relevanceRecall = self.relevanceRecall(nodesToChange, nodesToShare)
                    recallChange = self.relevanceRecallChanged(nodesToChange, nodesToShare, agent,focusObj = nodesToChange[0])
                    precision = self.relevancePrecision(nodesToChange, nodesToShare)
                    
                    
                    
                    distFromFocus = self.distanceFromFocusMetric(nodesToChange[0], nodesToShare)
                    
                    info = {} #dict holding nodes and their colors (to share with agent)
                    for node in nodesToShare:
                        if node in self.instance.graph.nodes():
                            info[node] = self.instance.getColor(node)
                        else:
                            info[node]=-2 #-2 = removed!
                    
                    changedBelief = agent.updateBelief(info,self.instance.graph) #update agents knowledge, also sending the graph so they know neighbors for added objects
                    if len(changedBelief)!=len(nodesToShare):
                        print 'problem'

                    precisionChangedByOther = self.precisionChangedByOtherAgent(nodesToChange, nodesToShare, agent)
                    actions = agent.chooseActions(self.numIterations,minActions = 0, nextID = self.nextNodeID) #query agent for actions
                    
                    
                    stateWithout = self.instance.getGraphState() #TODO: if not forcing agent to choose specific nodes, can't do this!
                    
                    #send update to system; update problem instance and clusters
                    actionObjs = []
                    index = 0
                    print 'nodesToChange'+str(nodesToChange)
                    print 'actions '+str(actions)
#                    for node,col in actions:
                    for index in range(len(nodesToChange)):
                        objAct = actions[nodesToChange[index]]
                        node = objAct[0]
                        col = objAct[1]
                        if col == -2: #removing existing obj
                            print 'in sim: removing node '+str(node)
                            #new action object to send to systems
                            actionObj = Action(agent.id, node, 'sigEdit', col, self.weightIncOfAction, 1.0)
                            actionObjs.append(actionObj)
                            #remove object from graph
                            self.instance.graph.node[node]['color']=-2 #mark as removed, but don't actually remove
                            #remove object from clusters
                            clusterNum = self.nodeToClusterIndex[node]
                            print 'clusterNum ='+str(clusterNum)
                            print 'cluster: '+ str(self.clusters[clusterNum])
                            self.clusters[clusterNum].remove(node)
                            #TODO: think about whether to also remove from index [probably NOT]
                            for a in self.agents:
                                a.removeNodeFromCluster(node,clusterNum)                            
                        elif col == -3: #adding new obj
                            #new action object to send to systems
                            actionObj = Action(agent.id, node, 'sigEdit', col, self.weightIncOfAction, 1.0)
                            actionObjs.append(actionObj) 
                            #add object to graph
                            attr = {}
                            attr['color']=-1
                            print 'in sim: addding node '+str(node)
                            self.instance.graph.add_node(node,attr)
                            self.nextNodeID= self.nextNodeID+1
                            
                            print 'index = '+str(index)
                            
                            self.instance.graph.add_edge(node,nodesToChange[index]) #adding the edge between the object to which the new object was connected

                            newNodeCluster = self.nodeToClusterIndex[nodesToChange[index]]
                            self.clusters[newNodeCluster].append(node) #adding the new node to the cluster
                            self.nodeToClusterIndex[node]=newNodeCluster #adding the new node to index of clusters by nodes
                            #add new edges based on distributions
                            self.connectNewNode(node) 
                            
                        else:
                            actionObj = Action(agent.id, node, 'sigEdit', col, self.weightIncOfAction, 1.0)
                            actionObjs.append(actionObj)     
                            #send real update to GraphProblem
                            print 'node = '+str(node)
                            print 'col = '+str(col)
                            change = {}
                            change[node]=col
                            self.instance.updateGraph(change)                                                                                  
                            
                    session = Session(agent.id, actionObjs, self.numIterations, nodesToShare)
                    system.update(session) #send info back to system
                    
                    #update last changed by
                    for n in nodesToChange:
                        self.lastChangedBy[n] = agent
                    
                    #save status
                    res = {}
                    res['graphName'] = graphName
                    res['fromScratch']=self.fromScratch
                    res['algorithm'] = system
                    res['iteration'] = self.numIterations
                    res['round'] = math.floor(float(self.numIterations)/self.numAgents)
                    res['focus'] = self.focus
                    res['queryLimit']=self.queryLimit
                    res['actionLimit']=self.actionLimit
                    res['numAgents']=self.numAgents
                    res['numNodes']=nx.number_of_nodes(self.graph)
                    res['numEdges']=nx.number_of_edges(self.graph)
                    res['pWithin']=self.pWithin
                    res['pBetween']=self.pBetween
                    res['probPrimaryCluster']= self.probPrimay
                    
                    

                    
                    

                    
                    state = self.instance.getGraphState()
                    
                    confDiff =  state['conflicts']-stateWithout['conflicts'] #positive is good!
                        
                    res['relevance'] = relevance
                    res['relevanceBinary'] = relevanceBinary 
                    res['recall'] = recallChange      
                    res['precision'] =  precision        
                    res['precisionChanged']=precisionChangedByOther  
                    res['AverageDistance'] = distFromFocus 
                    
                    res['conflicts'] = state['conflicts']
                    res['unknown'] = state['unknown']
                    res['notConflicts'] = state['notConflicts']

                    res['confDiff']=confDiff
                    
                    res['percentColored'] = self.instance.getPercentColored() #only relevant if we start from nothing colored
                    res['run'] = run
                    
                    results.append(res)
                    
#                    filename = "../graphPlots1/"+str(system)+"_"+str(self.numIterations)+".png"
#                    if self.numIterations == 0:
#                        self.instance.drawGraph(filename)
                    
                    #increment num of iterations
                    self.numIterations = self.numIterations + 1
                    print 'graph nodes :'+str(self.instance.graph.nodes())
            
            #save results
#            res = Result(system, self.numIterations, self.instance.getGraphState(), self.instance.getPercentColored())
#            results[system] = res
            #revert graph and restart iterations counter
            self.instance = initialProblem
            self.numIterations = 0     
            print 'finished running algorithm: '+str(system)
                   
            
        #save results to file
        with open(self.outputFile, 'ab') as csvfile:
            fieldnames = ['graphName','fromScratch', 'algorithm', 'iteration', 'round','focus','queryLimit','actionLimit','numAgents','numNodes','numEdges','pWithin','pBetween','probPrimaryCluster','relevance','relevanceBinary','recall', 'precision','precisionChanged','AverageDistance','conflicts','unknown','notConflicts','confDiff','percentColored','run']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            for res in results:
                writer.writerow(res)
    
        
        
    def runSimulation(self, graphName, run = 0, learnTime = -1):

        #store results
        results = []
        #save initial state to revert for each system
        seed = np.random.randint(2)
        #run each system  
        sharedByRandSys = {} #for learning phase     
        for system in self.systems:
            initialProblem = copy.deepcopy(self.instance)
            self.agents = [] #reset agents
            
            for agent,nodes in self.agentAssignments.iteritems():
                newAgent = Agent(agent,nodes,copy.deepcopy(self.graph), self.colors,self.actionLimit, reset = False, seed = seed)
                self.agents.append(newAgent)            
            print 'starting to run algorithm: '+str(system)
            while ((self.solved == False) & (self.numIterations<self.maxIterations)): 
                for agent in self.agents: #agents iterate in round robin. #TODO: in future, consider non-uniform session

                    nodesToChange = agent.chooseNodesByDistribution() #agent chooses the nodes to change TODO: later possibly inform system of this choice

                    
                    #check what agent would have done without new info
                    actionsWithoutKnowledge = agent.chooseActionsDonotApply(self.numIterations,minActions = 0)
                    
                    #query system
                    if self.setting == "all":
                        if self.focus:
                            nodesToShare = system.query(agent.id, self.queryLimit, startRev=0, node = nodesToChange[0]) #get nodes info to share with agent. nodesToShare is list of nodes
                        else:
                            nodesToShare = system.query(agent.id, self.queryLimit, startRev=0, node = None)  
                    
                    else: #only ranking changes, need to send first rev to consider
                        if self.focus:
                            nodesToShare = system.query(agent.id, self.queryLimit, startRev = agent.lastRevision+1, node = nodesToChange[0]) 
                        else:    
                            nodesToShare = system.query(agent.id, self.queryLimit, startRev = agent.lastRevision+1, node = None)
                    
                    
                    #compute metrics
                    relevance = self.relevanceMetric(nodesToChange, nodesToShare)
                    relevanceBinary = self.relevanceMetricBinaryNodes(nodesToChange, nodesToShare)
                    relevanceRecall = self.relevanceRecall(nodesToChange, nodesToShare)
                    recallChange = self.relevanceRecallChanged(nodesToChange, nodesToShare, agent)
                    precision = self.relevancePrecision(nodesToChange, nodesToShare)
                    
                    
                    
                    distFromFocus = self.distanceFromFocusMetric(nodesToChange[0], nodesToShare)
                    
                    info = {} #dict holding nodes and their colors (to share with agent)
                    for node in nodesToShare:
                        info[node] = self.instance.getColor(node)
                    
                    changedBelief = agent.updateBelief(info) #update agents knowledge
                    if len(changedBelief)!=len(nodesToShare):
                        print 'problem'
                    precisionChangedNodes = self.relevancePrecisionChanged(nodesToChange, nodesToShare, changedBelief)
                    precisionChangedByOther = self.precisionChangedByOtherAgent(nodesToChange, nodesToShare, agent)
                    actions = agent.chooseActions(self.numIterations,minActions = 0) #query agent for actions
 
                    
                    #send update to system
                    actionObjs = []
                    for node,col in actions:
                        actionObj = Action(agent.id, node, 'sigEdit', col, self.weightIncOfAction, 1.0)
                        actionObjs.append(actionObj)
                    session = Session(agent.id, actionObjs, self.numIterations, nodesToShare)
                    system.update(session) #send info back to system
                    
                                        #update last changed by
                    for n in nodesToChange:
                        self.lastChangedBy[n] = agent
                    
                    #save status
                    res = {}
                    res['graphName'] = graphName
                    res['fromScratch']=self.fromScratch
                    res['algorithm'] = system
                    res['iteration'] = self.numIterations
                    res['round'] = math.floor(float(self.numIterations)/self.numAgents)
                    res['focus'] = self.focus
                    res['queryLimit']=self.queryLimit
                    res['actionLimit']=self.actionLimit
                    res['numAgents']=self.numAgents
                    res['numNodes']=nx.number_of_nodes(self.graph)
                    res['numEdges']=nx.number_of_edges(self.graph)
                    res['pWithin']=self.pWithin
                    res['pBetween']=self.pBetween
                    res['probPrimaryCluster']= self.probPrimay
                    
                    
                    #compute effect metric
                    diff = 0
                    for act1 in actions:
                            if act1 not in actionsWithoutKnowledge:
                                diff = 1
                                break
                            
                    #check constraints with and without sharing the info
#                    self.instance.updateGraph(actionsWithoutKnowledge)
#                    stateWithout = self.instance.getGraphState() #TODO: if not forcing agent to choose specific nodes, can't do this!
                    
                    #send real update to GraphProblem
                    self.instance.updateGraph(actions)
                    
                    state = self.instance.getGraphState()
                    
#                    confDiff =  state['conflicts']-stateWithout['conflicts'] #positive is good!
                        
                    res['relevance'] = relevance
                    res['relevanceBinary'] = relevanceBinary 
                    res['recall'] = recallChange      
                    res['precision'] =  precision        
                    res['precisionChanged']=precisionChangedByOther  
                    res['AverageDistance'] = distFromFocus 
                    
                    res['conflicts'] = state['conflicts']
                    res['unknown'] = state['unknown']
                    res['notConflicts'] = state['notConflicts']

                    res['effect']=  diff                 
#                    res['confDiff']=confDiff
                    
                    res['percentColored'] = self.instance.getPercentColored() #only relevant if we start from nothing colored
                    res['run'] = run
                    
                    results.append(res)
                    
#                    filename = "../graphPlots1/"+str(system)+"_"+str(self.numIterations)+".png"
#                    if self.numIterations == 0:
#                        self.instance.drawGraph(filename)
                    
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
        with open(self.outputFile, 'ab') as csvfile:
            fieldnames = ['graphName','fromScratch', 'algorithm', 'iteration', 'round','focus','queryLimit','actionLimit','numAgents','numNodes','numEdges','pWithin','pBetween','probPrimaryCluster','relevance','relevanceBinary','recall', 'precision','precisionChanged','AverageDistance','conflicts','unknown','notConflicts','effect','percentColored','run']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            for res in results:
                writer.writerow(res)
            

    '''
    Run simulation with just precision-recall computation
    '''
    def runPRSimulation(self, graphName, run = 0, learnTime = -1):

        #store results
        results = []
        #save initial state to revert for each system
        seed = np.random.randint(2)
        #run each system  
        sharedByRandSys = {} #for learning phase     
        for system in self.systems:
            initialProblem = copy.deepcopy(self.instance)
            self.agents = [] #reset agents
            
            for agent,nodes in self.agentAssignments.iteritems():
                newAgent = Agent(agent,nodes,copy.deepcopy(self.graph), self.colors,self.actionLimit, reset = False, seed = seed)
                self.agents.append(newAgent)            
            print 'starting to run algorithm: '+str(system)
            while ((self.solved == False) & (self.numIterations<self.maxIterations)): 
                for agent in self.agents: #agents iterate in round robin. #TODO: in future, consider non-uniform session

                    nodesToChange = agent.chooseNodesByDistribution() #agent chooses the nodes to change TODO: later possibly inform system of this choice


                    if self.focus:
                        nodesToShare = system.queryList(agent.id, self.queryLimit, startRev=0, node = nodesToChange[0]) #get nodes info to share with agent. nodesToShare is list of nodes
                    else:
                        nodesToShare = system.queryList(agent.id, self.queryLimit, startRev=0, node = None)  
                    
                    nodesToShareRestricted = nodesToShare[:self.queryLimit]                  
                    info = {} #dict holding nodes and their colors (to share with agent)
                    for node in nodesToShareRestricted:
                        info[node] = self.instance.getColor(node)
                    
                    changedBelief = agent.updateBelief(info) #update agents knowledge
                   
                    #compute metrics
                    for i in range(1,len(nodesToShare)+1):
                        res = {}
                        res['algorithm'] = system
                        res['iteration'] = self.numIterations
                        res['round'] = math.floor(float(self.numIterations)/self.numAgents)   
                        res['run'] = run                     
                        recallChange = self.relevanceRecallChanged(nodesToChange, nodesToShare[:i], agent,nodesToChange[0])
                        precisionChangedByOther = self.precisionChangedByOtherAgent(nodesToChange, nodesToShare[:i], agent)
                        res['queryLimit']=i
                        res['precision']=precisionChangedByOther
                        res['recall']=recallChange
                        results.append(res)
                    
                    actions = agent.chooseActions(self.numIterations,minActions = 0) #query agent for actions
 
                    
                    #send update to system
                    actionObjs = []
                    for node,col in actions:
                        actionObj = Action(agent.id, node, 'sigEdit', col, self.weightIncOfAction, 1.0)
                        actionObjs.append(actionObj)
                    session = Session(agent.id, actionObjs, self.numIterations, nodesToShare)
                    system.update(session) #send info back to system
                    
                                        #update last changed by
                    for n in nodesToChange:
                        self.lastChangedBy[n] = agent
  
                    #send real update to GraphProblem
                    self.instance.updateGraph(actions)
                    
                    
                    
                   
                    
                    
                    #increment num of iterations
                    self.numIterations = self.numIterations + 1
                    
            

            #revert graph and restart iterations counter
            self.instance = initialProblem
            self.numIterations = 0     
            print 'finished running algorithm: '+str(system)
                   
            
        #save results to file
        with open("../results/precisionRecall_agents5_actionLimit3.csv", 'ab') as csvfile:
            fieldnames = ['algorithm','iteration', 'round', 'run', 'queryLimit','precision','recall']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

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
    sim.runSimulation(filename,graphName, learnTime = 30)      
    
def frange(start,stop, step=1.0):
    while start < stop:
        yield start
        start +=step    
    
if __name__ == '__main__':
    simType = "dynamic"
    
    nodesPerCluster = 8
    pWithin = 0.3
    pBetween = 0.08
    graphName = 'clustered_'+str(nodesPerCluster)+"_"+str(pWithin)+"_"+str(pBetween)
    
    if simType == "dynamic":
        maxIterations = 100
        for numAgents in (3,5):
            for actionLimit in (3,5):
                outputFile =   '../results/0820/0820_agents_'+str(numAgents)+'actionLimit_'+str(actionLimit)+'primaryProg0.8_Focus_onlyChanged.csv'
    
                    #write header row in file:
                with open(outputFile, 'ab') as csvfile:
                    fieldnames = ['graphName','fromScratch', 'algorithm', 'iteration', 'round','focus','queryLimit','actionLimit','numAgents','numNodes','numEdges','pWithin','pBetween','probPrimaryCluster','relevance','relevanceBinary','recall', 'precision','precisionChanged','AverageDistance','conflicts','unknown','notConflicts','effect','confDiff','percentColored','run']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()         
            
                for queryLimit in (1,3,5):
                    nodesP = [12]
                    for nodesPerCluster in (nodesP):
                        pw = [0.3,0.4]
                        for pWithin in pw:
                            for pBetween in (0.05,0.15):
                                systems = []
                                randSys = RandomSystem()
                                mostChanged = MostChangedInIntervalSystem(500) #essentially all revisions...
                                mostChangeInt = MostChangedInIntervalSystem(5)
                                latestSys = LatestChangedSystem()
                                
                                mipAlpha= Mip(alpha = 1.0, beta1 = 0.0, beta2 = 0.0, gamma = 0.0, decay = 0.0)
                                mipBeta1= Mip(alpha = 0.0, beta1 = 1.0, beta2 = 0.0, gamma = 0.0, decay = 0.0)
                                mipBeta2= Mip(alpha = 0.0, beta1 = 0.0, beta2 = 1.0, gamma = 0.0, decay = 0.0)
                                mipGamma= Mip(alpha = 0.0, beta1 = 0.0, beta2 = 0.0, gamma = 1.0, decay = 0.0)
        #                        mip = Mip(alpha = 0.4, beta = 0.4, gamma = 0.2)
                                mip1 = Mip(alpha = 0.2, beta1 = 0.3, beta2 = 0.3, gamma = 0.2, decay = 0.0)
                                mip2 = Mip(alpha = 0.1, beta1 = 0.4, beta2 = 0.4, gamma = 0.1, decay = 0.0)
                                mip3 = Mip(alpha = 0.1, beta1 = 0.5, beta2 = 0.3, gamma = 0.1, decay = 0.0)
                                mip4 = Mip(alpha = 0.0, beta1 = 0.5, beta2 = 0.4, gamma = 0.1, decay = 0.0)
    #                            mipAlphaND= Mip(alpha = 1.0, beta = 0.0, gamma = 0.0, decay = 0.0)
    #                            mipBetaND= Mip(alpha = 0.0, beta = 1.0, gamma = 0.0, decay = 0.0)
    #                            mipGammaND= Mip(alpha = 0.0, beta = 0.0, gamma = 1.0, decay = 0.0)
    #    #                        mip = Mip(alpha = 0.4, beta = 0.4, gamma = 0.2)
    #                            mip2ND = Mip(alpha = 0.5, beta = 0.3, gamma = 0.2, decay = 0.0)
                                systems.append(randSys)
#                                systems.append(mostChanged)
#    #                            
#    #                            
#    #  #                          systems.append(mostChangeInt)
#                                systems.append(latestSys)  
#    #                              
#                                systems.append(mipAlpha) 
#                                systems.append(mipBeta1) 
#                                systems.append(mipBeta2) 
#                                systems.append(mipGamma)
#    #                            systems.append(mip2)
#                                
#                                systems.append(mip1) 
#                                systems.append(mip2) 
#                                systems.append(mip3) 
#                                systems.append(mip4)
    #                            systems.append(mip2ND)                            
                                 
                                sim = Simulation(numAgents, 3, systems, numNodesPerCluster=nodesPerCluster,pWithin=pWithin, pBetween=pBetween, outputFile =outputFile,fromScratch = True, focus = True, probPrimary = 0.8, overlap = 2, maxIterations = maxIterations, actionLimit = actionLimit, queryLimit = queryLimit, weightInc = 1.0, setting = "all")
                                systemsBeforeRun = copy.deepcopy(systems)
                    #            filename= '../results/0730/test_focus_colored_'+graphName+"_iterations"+str(maxIterations)+"_queryLimit"+str(queryLimit)+"_actionLimit"+str(actionLimit)+"_agents"+str(numAgents)+".csv"
                                for i in range(5):  
                                    systemsBeforeRun = copy.deepcopy(systemsBeforeRun)               
                                    sim.runSimulationDynamic(graphName, run = i, learnTime = 0)
                                    sim.resetSystems(systemsBeforeRun)          
    if simType=='PR':
        maxIterations = 50
        numAgents=5
        actionLimit = 3
        nodesP = [8]
        for nodesPerCluster in (nodesP):
            pw = [0.3]
            for pWithin in pw:
                pBetween = 0.05
                systems = []
                randSys = RandomSystem()
                mostChanged = MostChangedInIntervalSystem(500) #essentially all revisions...
                mostChangeInt = MostChangedInIntervalSystem(5)
                latestSys = LatestChangedSystem()
                
                mipAlpha= Mip(alpha = 1.0, beta1 = 0.0, beta2 = 0.0, gamma = 0.0, decay = 0.0)
                mipBeta1= Mip(alpha = 0.0, beta1 = 1.0, beta2 = 0.0, gamma = 0.0, decay = 0.0)
                mipBeta2= Mip(alpha = 0.0, beta1 = 0.0, beta2 = 1.0, gamma = 0.0, decay = 0.0)
                mipGamma= Mip(alpha = 0.0, beta1 = 0.0, beta2 = 0.0, gamma = 1.0, decay = 0.0)
#                        mip = Mip(alpha = 0.4, beta = 0.4, gamma = 0.2)
                mip1 = Mip(alpha = 0.2, beta1 = 0.3, beta2 = 0.3, gamma = 0.2, decay = 0.0)
                mip2 = Mip(alpha = 0.1, beta1 = 0.4, beta2 = 0.4, gamma = 0.1, decay = 0.0)
                mip3 = Mip(alpha = 0.1, beta1 = 0.5, beta2 = 0.3, gamma = 0.1, decay = 0.0)
                mip4 = Mip(alpha = 0.0, beta1 = 0.5, beta2 = 0.4, gamma = 0.1, decay = 0.0)
#                            mipAlphaND= Mip(alpha = 1.0, beta = 0.0, gamma = 0.0, decay = 0.0)
#                            mipBetaND= Mip(alpha = 0.0, beta = 1.0, gamma = 0.0, decay = 0.0)
#                            mipGammaND= Mip(alpha = 0.0, beta = 0.0, gamma = 1.0, decay = 0.0)
#    #                        mip = Mip(alpha = 0.4, beta = 0.4, gamma = 0.2)
#                            mip2ND = Mip(alpha = 0.5, beta = 0.3, gamma = 0.2, decay = 0.0)
                systems.append(randSys)
                systems.append(mostChanged)
#                            
#                            
#  #                          systems.append(mostChangeInt)
                systems.append(latestSys)  
#                              
                systems.append(mipAlpha) 
                systems.append(mipBeta1) 
                systems.append(mipBeta2) 
                systems.append(mipGamma)
#                            systems.append(mip2)
                
                systems.append(mip1) 
                systems.append(mip2) 
                systems.append(mip3) 
                systems.append(mip4)
#                            systems.append(mip2ND)                            
                 
                sim = Simulation(numAgents, 3, systems, numNodesPerCluster=nodesPerCluster,pWithin=pWithin, pBetween=pBetween, outputFile ="file.csv",fromScratch = True, focus = True, probPrimary = 0.8, overlap = 2, maxIterations = maxIterations, actionLimit = actionLimit, queryLimit = 3, weightInc = 1.0, setting = "all")
                systemsBeforeRun = copy.deepcopy(systems)
    #            filename= '../results/0730/test_focus_colored_'+graphName+"_iterations"+str(maxIterations)+"_queryLimit"+str(queryLimit)+"_actionLimit"+str(actionLimit)+"_agents"+str(numAgents)+".csv"
                for i in range(5):  
                    systemsBeforeRun = copy.deepcopy(systemsBeforeRun)               
                    sim.runPRSimulation(graphName, run = i, learnTime = 0)
                    sim.resetSystems(systemsBeforeRun)          
    else:
        maxIterations = 100
        for numAgents in (3,5):
            for actionLimit in (3,5):
                outputFile =   '../results/0811/0811_agents_'+str(numAgents)+'actionLimit_'+str(actionLimit)+'primaryProg0.8_Focus_onlyChanged.csv'
    
                    #write header row in file:
                with open(outputFile, 'ab') as csvfile:
                    fieldnames = ['graphName','fromScratch', 'algorithm', 'iteration', 'round','focus','queryLimit','actionLimit','numAgents','numNodes','numEdges','pWithin','pBetween','probPrimaryCluster','relevance','relevanceBinary','recall', 'precision','precisionChanged','AverageDistance','conflicts','unknown','notConflicts','effect','confDiff','percentColored','run']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()         
            
                for queryLimit in (1,3,5):
                    nodesP = [8]
                    for nodesPerCluster in (nodesP):
                        pw = [0.3,0.4]
                        for pWithin in pw:
                            for pBetween in (0.05,0.15):
                                systems = []
                                randSys = RandomSystem()
                                mostChanged = MostChangedInIntervalSystem(500) #essentially all revisions...
                                mostChangeInt = MostChangedInIntervalSystem(5)
                                latestSys = LatestChangedSystem()
                                
                                mipAlpha= Mip(alpha = 1.0, beta1 = 0.0, beta2 = 0.0, gamma = 0.0, decay = 0.0)
                                mipBeta1= Mip(alpha = 0.0, beta1 = 1.0, beta2 = 0.0, gamma = 0.0, decay = 0.0)
                                mipBeta2= Mip(alpha = 0.0, beta1 = 0.0, beta2 = 1.0, gamma = 0.0, decay = 0.0)
                                mipGamma= Mip(alpha = 0.0, beta1 = 0.0, beta2 = 0.0, gamma = 1.0, decay = 0.0)
        #                        mip = Mip(alpha = 0.4, beta = 0.4, gamma = 0.2)
                                mip1 = Mip(alpha = 0.2, beta1 = 0.3, beta2 = 0.3, gamma = 0.2, decay = 0.0)
                                mip2 = Mip(alpha = 0.1, beta1 = 0.4, beta2 = 0.4, gamma = 0.1, decay = 0.0)
                                mip3 = Mip(alpha = 0.1, beta1 = 0.5, beta2 = 0.3, gamma = 0.1, decay = 0.0)
                                mip4 = Mip(alpha = 0.0, beta1 = 0.5, beta2 = 0.4, gamma = 0.1, decay = 0.0)
    #                            mipAlphaND= Mip(alpha = 1.0, beta = 0.0, gamma = 0.0, decay = 0.0)
    #                            mipBetaND= Mip(alpha = 0.0, beta = 1.0, gamma = 0.0, decay = 0.0)
    #                            mipGammaND= Mip(alpha = 0.0, beta = 0.0, gamma = 1.0, decay = 0.0)
    #    #                        mip = Mip(alpha = 0.4, beta = 0.4, gamma = 0.2)
    #                            mip2ND = Mip(alpha = 0.5, beta = 0.3, gamma = 0.2, decay = 0.0)
                                systems.append(randSys)
                                systems.append(mostChanged)
    #                            
    #                            
    #  #                          systems.append(mostChangeInt)
                                systems.append(latestSys)  
    #                              
                                systems.append(mipAlpha) 
                                systems.append(mipBeta1) 
                                systems.append(mipBeta2) 
                                systems.append(mipGamma)
    #                            systems.append(mip2)
                                
                                systems.append(mip1) 
                                systems.append(mip2) 
                                systems.append(mip3) 
                                systems.append(mip4)
    #                            systems.append(mip2ND)                            
                                 
                                sim = Simulation(numAgents, 3, systems, numNodesPerCluster=nodesPerCluster,pWithin=pWithin, pBetween=pBetween, outputFile =outputFile,fromScratch = True, focus = True, probPrimary = 0.8, overlap = 2, maxIterations = maxIterations, actionLimit = actionLimit, queryLimit = queryLimit, weightInc = 1.0, setting = "all")
                                systemsBeforeRun = copy.deepcopy(systems)
                    #            filename= '../results/0730/test_focus_colored_'+graphName+"_iterations"+str(maxIterations)+"_queryLimit"+str(queryLimit)+"_actionLimit"+str(actionLimit)+"_agents"+str(numAgents)+".csv"
                                for i in range(5):  
                                    systemsBeforeRun = copy.deepcopy(systemsBeforeRun)               
                                    sim.runSimulation(graphName, run = i, learnTime = 0)
                                    sim.resetSystems(systemsBeforeRun)  
                        
                        
