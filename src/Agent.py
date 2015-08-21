'''
Created on Jun 7, 2015

@author: Ofra
'''
import networkx as nx
import math
import copy
import random
from random import shuffle

class Agent:
    def __init__(self, id, clusters, knownGraph, colors, actionLimit, reset, seed = 10, pPrimary = 0.8):
        self.id = id
        self.controlledNodes = clusters
        self.knownGraph = knownGraph
        self.actionLimit = actionLimit #number of change color actions allowed per round
        self.colors = colors #possible colors
        self.lastRevision = -1 
        self.actionTypes = {}
        random.seed(seed)
        #the graph sent by simulation has the colors, need to remove them for each agent
        for node, data in self.knownGraph.nodes(data = True):
            data['color']= -1 #for testing, might need to change (start with knowing some colors)
            data['uptoDate']= False
        
        self.reset = reset #controls agents' "memory" 
        self.graphState = {}; #will hold current known numbers for 'conflicts' 'notConflicts' and 'unknown'
        self.countNumConflicts()
        self.nodesToChange = [] #will hold the nodes chosen for the round
        self.probPrimary = pPrimary
        
    #count initial number of conflicts
    def countNumConflicts(self):
        #counters of updates to conflicts
        unknown = 0
        conf = 0
        nonConf = 0 
        for u,v in self.knownGraph.edges_iter():
#            print 'u = '+str(u) + ", v = "+str(v)
            try:
                colU = self.knownGraph.node[u]['color']
                colV = self.knownGraph.node[v]['color']
            except:
                print 'u = '+str(u)+' v = '+str(v)
            colU = self.knownGraph.node[u]['color']
            colV = self.knownGraph.node[v]['color']                 
#            print 'colU = '+ str(colU)+", colV = "+str(colV)
            if ((colU == -1) | (colV == -1)):
                unknown = unknown + 1
            elif colU == colV:
                conf = conf+1
            else:
                nonConf = nonConf + 1
                
        self.graphState['conflicts'] = conf
        self.graphState['notConflicts'] = nonConf
        self.graphState['unknown'] = unknown

        return  
    
    #the function updates the agents' knowledge about the graph
    #nodesColorsList is a dict of node_id and current color
    def updateBelief(self, nodesColorsList, problemInstance = None, clustersReal = None):
        changedBelief = []
        
        #reset old stuff
        if self.reset == True:
            for node, data in self.knownGraph.nodes(data = True):
                if data['uptoDate']== True: # if node was uptoDate in the last turn, treat the color unchanged but reset uptoDate so next turn it gets reset
                    data['uptoDate']= False
                else: #the node is not uptodate, reset the color to unknown
                    data['color'] = -1
        
        #update new stuff
        if isinstance(nodesColorsList, list): #local update belief from the agent's choice of actions [list]
            for node,color in nodesColorsList:
                changed = 0
                if self.knownGraph.node[node]['color'] != color:
                    changed = 1
                changedBelief.append(changed)
                self.knownGraph.node[node]['color'] = color
                self.knownGraph.node[node]['uptoDate'] = True
        else: #change of belief based on information from system [dict]
            for node,color in nodesColorsList.iteritems():
#                print 'node = '+str(node)
#                print 'color ='+str(color)
                changed = 0
                if node in self.knownGraph.nodes():
                    if self.knownGraph.node[node]['color'] != color:
                        changed = 1  
                    changedBelief.append(changed)
                    if color>-2:
                        self.knownGraph.node[node]['color'] = color 
                    elif color==-2: #add new vertex
                        self.knownGraph.remove_node(node) 
  
#                    self.knownGraph.node[node]['uptoDate'] = True   
                else: #learned about a new node, need to add it to the graph as well as all the edges
                    attr = {}
                    attr['color']=color
                    self.knownGraph.add_node(node,attr)
#                    print 'color of node: '+str(self.knownGraph.node[node]['color'])
                    neighbors = nx.neighbors(problemInstance, node)
                    for ne in neighbors:
                        if ne in self.knownGraph.nodes():
                            self.knownGraph.add_edge(node,ne)   
                    clustToAddTo = self.findNodeCluster(clustersReal, node)  
                    if clustToAddTo!=-1: #otherwise we have a situation where a node was added and removed before the agent saw it!   
                        self.controlledNodes[clustToAddTo].append(node)
#                        print 'added to controlled nodes: '+str(self.controlledNodes)
        self.countNumConflicts() #update conflict counts

        return changedBelief
    
    def findNodeCluster(self,clusters, node):
#        print 'clusters: '+str(clusters)
#        print 'node = '+str(node)
        for clust in clusters.keys():
            if node in clusters[clust]:
                return clust
        return -1
    
    def checkRep(self):
        for i in range(self.nodesToChange):
            for j in range(i+1,self.nodesToChange):
                if i == j:
                    print 'problem'
        return 1


    def objExists(self,nodeID): 
        for clust in self.controlledNodes.keys():
            if nodeID in self.controlledNodes[clust]:
                return True
        return False
    
    '''
    chooses k actions in the following way: pick first node based on distribution. Then, pick k-1 more nodes that are on a path (without repeating any node)
    '''
    def chooseNodesByDistributionDynamic(self):
#        try:
        self.nodesToChange = [] #reset from previous turns 
        #choose first node based on distribution
#        print 'controlled Nodes: '+str(self.controlledNodes)
        rand = random.random()
        cumProb = 0.0
        currIndex = 0
        clustNum = self.id
        if ((rand<self.probPrimary) & (len(self.controlledNodes[self.id])>0)): #choose object from primary cluster
            clustNum = self.id
        else:
            tries = 0
            while ((clustNum==self.id) | (len(self.controlledNodes[clustNum])==0)): #choose object from a different cluster
                clustNum = random.randint(0,len(self.controlledNodes)-1)
                if tries>100:
                    clustNum = self.id
                    break
                tries= tries+1
        
        objIndex = random.randint(0,len(self.controlledNodes[clustNum])-1)
        chosenNode = copy.deepcopy(self.controlledNodes[clustNum][objIndex])
            
        currNode = chosenNode
        self.nodesToChange.append(chosenNode)
        #get remaining nodes from neighbors
        neighbors = nx.neighbors(self.knownGraph, currNode)
        validNeighbors = [x for x in neighbors if self.objExists(x)==True]
        additionalNodes = random.sample(validNeighbors,min(self.actionLimit-1,len(validNeighbors)))
        self.nodesToChange.extend(additionalNodes)
        
        if len(self.nodesToChange)<self.actionLimit: #need to get more nodes
            neighborsNeighbors = []
            for i in range(1,len(self.nodesToChange)):
                neighborsNeighbors.extend(nx.neighbors(self.knownGraph, self.nodesToChange[i]))
            extensionList = [x for x in neighborsNeighbors if ((x not in self.nodesToChange) & (self.objExists(x)==True))]
            moreNodes = random.sample(extensionList,min(self.actionLimit-len(self.nodesToChange),len(extensionList)))
            self.nodesToChange.extend(moreNodes)
        
        for node in self.nodesToChange:
            if self.nodesToChange.count(node)>1:
                print "why?" 
                
        list(set(self.nodesToChange))     #in case we somehow have duplicates              
       
        return self.nodesToChange
        
    '''
    chooses k actions in the following way: pick first node based on distribution. Then, pick k-1 more nodes that are on a path (without repeating any node)
    '''
    def chooseNodesByDistribution(self):
#        try:
        self.nodesToChange = [] #reset from previous turns 
        #choose first node based on distribution
        
        rand = random.random()
        cumProb = 0.0
        currIndex = 0
        currNode = self.controlledNodes[currIndex]
        cumProb = cumProb+currNode[1]
        while rand>cumProb:
            currIndex = currIndex+1
            currNode = self.controlledNodes[currIndex]
            cumProb = cumProb+currNode[1]
        chosenNode = copy.deepcopy(currNode[0])
        currNode = chosenNode
        self.nodesToChange.append(chosenNode)
        #get remaining nodes from neighbors
        neighbors = nx.neighbors(self.knownGraph, currNode)
        additionalNodes = random.sample(neighbors,min(self.actionLimit-1,len(neighbors)))
        self.nodesToChange.extend(additionalNodes)
        
        if len(self.nodesToChange)<self.actionLimit: #need to get more nodes
            neighborsNeighbors = []
            for i in range(1,len(self.nodesToChange)):
                neighborsNeighbors.extend(nx.neighbors(self.knownGraph, self.nodesToChange[i]))
            extensionList = [x for x in neighborsNeighbors if x not in self.nodesToChange]
            moreNodes = random.sample(extensionList,min(self.actionLimit-len(self.nodesToChange),len(extensionList)))
            self.nodesToChange.extend(moreNodes)
        
        for node in self.nodesToChange:
            if self.nodesToChange.count(node)>1:
                print "why?" 
                
        list(set(self.nodesToChange))     #in case we somehow have duplicates              
       
        return self.nodesToChange
    
    def removeNodeFromCluster(self, node,cluster):
        if node in self.controlledNodes[cluster]:
            self.controlledNodes[cluster].remove(node)
#            print 'removed'
        else:
            'did not know about'
        
    
    '''
    choose what to do with each object (add neighbor, remove object, modify color)
    '''
    def chooseActionTypes(self, pModify, pAdd, pRemove):
        self.actionTypes = {} #remove = -1, add = 1, modify = 0
        for n in self.nodesToChange:
            rand = random.random()
#            print 'rand = '+str(rand)
            if rand<pModify:
                self.actionTypes[n]= 0
            elif rand<pAdd:
                self.actionTypes[n] = 1
            else:
                self.actionTypes[n] = -1
                
        return self.actionTypes
                
    def addObject(self, fromObject, nextID):
        newObjectID = nextID
        attr = {}
        attr['color']=-1
        self.knownGraph.add_node(newObjectID,attr)
        self.knownGraph.add_edge(fromObject,newObjectID)
        self.nodesToChange.remove(fromObject)
        clustNum = self.getClusterForNode(fromObject)
        self.controlledNodes[clustNum].append(nextID)
    
    def getClusterForNode(self,nodeId):    
        for i in range (len(self.controlledNodes)):
            if nodeId in self.controlledNodes[i]:
                return i
        return -1
    
    def removeObject(self, objectToRemove):
        self.knownGraph.node[objectToRemove]['color']=-2 #mark as removed
        self.nodesToChange.remove(objectToRemove)
        clust = self.getClusterForNode(objectToRemove)
        self.controlledNodes[clust].remove(objectToRemove)
         
    
    def chooseNodesByDistributionOld(self):
#        try:
        self.nodesToChange = [] #reset from previous turns 
        #choose first node based on distribution
        
        rand = random.random()
        cumProb = 0.0
        currIndex = 0
        currNode = self.controlledNodes[currIndex]
        cumProb = cumProb+currNode[1]
        while rand>cumProb:
            currIndex = currIndex+1
            currNode = self.controlledNodes[currIndex]
            cumProb = cumProb+currNode[1]
        chosenNode = copy.deepcopy(currNode[0])
        currNode = chosenNode
        self.nodesToChange.append(chosenNode)
        #get remaining nodes from neighbors
        for i in range(self.actionLimit-1): #TODO: consider randomizing number of nodes chosen; consider prioritizing just neighbors of first node
            newNode = random.sample(nx.neighbors(self.knownGraph, currNode),1)
            while ((len(newNode)==0)):
                newNode = random.sample(nx.neighbors(self.knownGraph, currNode),1)
                if newNode in self.nodesToChange:
                    print 'why?'
            self.nodesToChange.append(newNode[0])
            currNode = newNode[0]
        for i in range(len(self.nodesToChange)):
            for j in range(i+1,len(self.nodesToChange)):
                if self.nodesToChange[i] == self.nodesToChange[j]:
                    print 'problem'
       
        return self.nodesToChange    
#        except:
#            return self.chooseNodesByDistribution()
            

    #chooses the color changes made by the agent.
    #limit is the maximum number of nodes that the agent is allowed to change in one round
    #this version does not update the agent's belief (for simply querying)
    def chooseActionsDonotApply(self, revision, minActions = 0):
        
        self.lastRevision = revision
        initialSolution = {}
        initialSolution['actionSet'] = []
        initialSolution['conflicts'] = 1000000
        initialSolution['unknown'] = 0
        initialSolution['notConflicts'] = 0
        
        initialBestSolution = {}
        initialBestSolution['actionSet'] = []
        initialBestSolution['conflicts'] = 1000000
        initialBestSolution['unknown'] = 0
        initialBestSolution['notConflicts'] = 0        
        
        if len(self.nodesToChange)>0: #need to choose colors for *given* nodes
            bestSolution = self.chooseActionsRecurNodeSetGiven(initialSolution,0,initialBestSolution, minActions)
        else: #choose best actions given knowledge
            bestSolution = self.chooseActionsRecur(initialSolution,0,initialBestSolution, minActions)
                    
        #return chosen solution
        return bestSolution['actionSet'];
    
    def getObjectActionFromSet(self,actionSet, objID):
        for objAct in actionSet:
            if objAct[0]==objID:
                return objAct[1]
    #chooses the color changes made by the agent.
    #limit is the maximum number of nodes that the agent is allowed to change in one round
    def chooseActions(self, revision, minActions = 0, nextID = 0):
        
        self.lastRevision = revision
        initialSolution = {}
        initialSolution['actionSet'] = []
        initialSolution['conflicts'] = 1000000
        initialSolution['unknown'] = 0
        initialSolution['notConflicts'] = 0
        
        initialBestSolution = {}
        initialBestSolution['actionSet'] = []
        initialBestSolution['conflicts'] = 1000000
        initialBestSolution['unknown'] = 0
        initialBestSolution['notConflicts'] = 0        
        
        actionSet = {}
        
        if len(self.nodesToChange)>0: #need to choose colors for *given* nodes
            if len(self.actionTypes)>0:
#                print self.actionTypes
                for obj,act in self.actionTypes.iteritems():
#                    print 'obj = '+str(obj)
#                    print 'act = '+str(act)
                    if act==-1:
                        self.removeObject(obj)
                        actionSet[obj]=(obj,-2)
                    elif act==1:
#                        'in agent, adding node '+str(nextID)
                        self.addObject(obj, nextID)
                        actionSet[obj]=(nextID,-3)
                        nextID = nextID+1
#                        actionSet.append((nextID,-3))

                        
                bestSolution = self.chooseActionsRecurNodeSetGiven(initialSolution,0,initialBestSolution, minActions)
                self.updateBelief(bestSolution['actionSet'])
                for objAct in bestSolution['actionSet']:
                    actionSet[objAct[0]]=objAct
                #return chosen solution
                return actionSet;        
            else: #choose best actions given knowledge
                bestSolution = self.chooseActionsRecurNodeSetGiven(initialSolution,0,initialBestSolution, minActions)
#                print 'in else'
                #update belief (agent just changed the node so it knows its color
                self.updateBelief(bestSolution['actionSet'])
                return bestSolution['actionSet']
        
        


#        for objAct in bestSolution['actionSet']:
#            actionSet[objAct[0]]=objAct
        #return chosen solution
        return actionSet;
    

    def chooseActionsRecurNodeSetGiven(self, currSolution, nodeCounter, bestSolution, minActions):
        #TODO: add caching of partial action sets as to not recompute stuff? prune solutions that won't have enough actions? (minActions)
        #stop condition - when we reached the limit of actions permitted, or when reached the last node we can change
        if nodeCounter == len(self.nodesToChange):
            if len(currSolution['actionSet'])>=minActions:
                if currSolution['conflicts'] < bestSolution['conflicts']: 
    #                print 'oldBest: '+str(bestSolution)
                    bestSolution=currSolution
    #                print 'newBest: '+str(bestSolution)
                #break ties in favor of more known non-conflicts (otherwise might bias towards doing nothing)   
                elif currSolution['conflicts'] == bestSolution['conflicts']:
                    if currSolution['notConflicts'] > bestSolution['notConflicts']:
                        bestSolution=currSolution
            return bestSolution
        else:
            #call function with all possible options for next node (not change, change to each of the colors that differ from the current color)
            for color in self.colors: #change current node and recall function with each option
#                print 'node counter = '+str(nodeCounter)+" color = "+str(color)
                newActionSet = copy.deepcopy(currSolution['actionSet'])
                newActionSet.append((self.nodesToChange[nodeCounter],color))
                newGraphState = self.computeNumConflicts(newActionSet)

                if newGraphState['conflicts']>bestSolution['conflicts']:
#                        print 'pruned: '+str(newActionSet)
#                        print 'best solution = '+str(bestSolution)
#                        print 'newGraphState = '+str(newGraphState)
                    continue;

                else:
                    newSolution = {}
                    newSolution['actionSet'] = newActionSet
                    newSolution['conflicts'] = newGraphState['conflicts']
                    newSolution['notConflicts'] = newGraphState['notConflicts']
                    newSolution['unknown'] = newGraphState['unknown']
                    bestSolution = self.chooseActionsRecurNodeSetGiven(newSolution,nodeCounter+1,bestSolution,minActions) #call function to check this action set                  
                        
        return bestSolution; 
    
    
    def chooseActionsRecur(self, currSolution, nodeCounter, bestSolution, minActions):
        #TODO: add caching of partial action sets as to not recompute stuff? prune solutions that won't have enough actions? (minActions)
        #stop condition - when we reached the limit of actions permitted, or when reached the last node we can change
        if ((len(currSolution['actionSet']) == self.actionLimit) | (nodeCounter == len(self.controlledNodes))):
            if len(currSolution['actionSet'])>=minActions:
                if currSolution['conflicts'] < bestSolution['conflicts']: 
    #                print 'oldBest: '+str(bestSolution)
                    
                    bestSolution=currSolution
    #                print 'newBest: '+str(bestSolution)
                    
                #break ties in favor of more known non-conflicts (otherwise might bias towards doing nothing)   
                elif currSolution['conflicts'] == bestSolution['conflicts']:
                    if currSolution['notConflicts'] > bestSolution['notConflicts']:
                        bestSolution=currSolution
            return bestSolution
        else:
            #call function with all possible options for next node (not change, change to each of the colors that differ from the current color)
            for color in self.colors: #change current node and recall function with each option
#                print 'node counter = '+str(nodeCounter)+" color = "+str(color)
                print 'controlled nodes = '+str(self.controlledNodes)
                if color != self.knownGraph.node[self.controlledNodes[nodeCounter]]['color']: #don't try the same color, that is equivalent to no action so should not "waste" real action on that
                    newActionSet = copy.deepcopy(currSolution['actionSet'])
                    newActionSet.append((self.controlledNodes[nodeCounter],color))
                    newGraphState = self.computeNumConflicts(newActionSet)

                    if newGraphState['conflicts']>bestSolution['conflicts']:
#                        print 'pruned: '+str(newActionSet)
#                        print 'best solution = '+str(bestSolution)
#                        print 'newGraphState = '+str(newGraphState)
                        continue;

                    else:
                        newSolution = {}
                        newSolution['actionSet'] = newActionSet
                        newSolution['conflicts'] = newGraphState['conflicts']
                        newSolution['notConflicts'] = newGraphState['notConflicts']
                        newSolution['unknown'] = newGraphState['unknown']
                        bestSolution = self.chooseActionsRecur(newSolution,nodeCounter+1,bestSolution,minActions) #call function to check this action set                  
            
           
            bestSolution = self.chooseActionsRecur(currSolution,nodeCounter+1,bestSolution,minActions) #don't include a change to this node in action set
                        
        return bestSolution;
                    
                    
    def computeNumConflicts(self,actionSet): 
        newGraphState = {} #dictionary with 'conflicts' 'notConflicts' and 'unknown'
        prevColors = {} #store previous colors to check changed conflicts
        newColors = {}
        #counters of updates to conflicts
        unknown = 0
        conf = 0
        nonConf = 0 
#        print actionSet
#        print len(actionSet)
        if len(actionSet) == 0:
            newGraphState['conflicts'] = self.graphState['conflicts']+conf
            newGraphState['notConflicts'] = self.graphState['notConflicts']+nonConf
            newGraphState['unknown'] = self.graphState['unknown']+unknown
            return newGraphState          
        pairsOfChanged = [] #will hold list of edges for which both nodes changed in current action set
        changedNodes = [actionSet[i][0] for i in range(len(actionSet))]
        
        for action in actionSet:
            prevColors[action[0]] = self.knownGraph.node[action[0]]['color'] #saving old color to see if conflicts changed
            newColors[action[0]] = action[1]
            #re-checking all neighbors of node that changed, except neighbors that include another changed node (will check them next)
            for n in self.knownGraph.neighbors(action[0]):
                node = self.knownGraph.node[n] #get data for node (for color)
                if n not in changedNodes:
                    if node['color']!=-1: #if the neighbor is uncolored, we move from unknown-> unknown which is not going to make any difference. 
                        if action[1]!=node['color']: #there is currently no conflict (and that is not because the neighboring node is not colored) 
                            if ((action[1]!=prevColors[action[0]]) & (prevColors[action[0]]==-1)): #unknown --> not conflict
                                unknown = unknown -1
                                nonConf = nonConf +1
                            elif action[1]==prevColors[action[0]]: #there was previously a conflict: conf --> nonConf
                                nonConf = nonConf+1
                                conf = conf -1
                        else: #we have a conflict! 
                            if prevColors[action[0]] == -1: #unknown --> conf
                                unknown = unknown - 1
                                conf = conf + 1
                            elif prevColors[action[0]]!=node['color']: #noConf-->conf
                                nonConf = nonConf - 1
                                conf = conf + 1
                elif action[0]<n: #add pair (avoid double adding by requiring smaller first)
                    pairsOfChanged.append((action[0],n))
        
        #finished changing nodes; check updates to conflicts when two nodes changed
        for n1,n2 in pairsOfChanged:
            if newColors[n1] != newColors[n2]: #currently, no conflict; could be no->no (nothing to do), yes->no or unknown->no
                if ((prevColors[n1]==-1) | (prevColors[n2]==-1)): #unknown->no
                    unknown = unknown-1
                    nonConf = nonConf+1
                elif prevColors[n1] == prevColors[n2]: #previously had conflict (couldn't be unknown cause we checked in previous if); yes -->no
                    conf = conf-1
                    nonConf = nonConf+1
            else: #we have a conflict. could be no-> yes, yes->yes (nothing to do), unknown->yes
                if ((prevColors[n1]==-1) | (prevColors[n2]==-1)): #unknown->yes
                    unknown = unknown-1
                    conf = conf+1 
                elif prevColors[n1] != prevColors[n2]: #previously did not have conflict (couldn't be unknown cause we checked in previous if); no -->yes
                    conf = conf+1
                    nonConf = nonConf-1                    
        
        #create object to return (computing numbers by adding updates to currently known numbers
        newGraphState['conflicts'] = self.graphState['conflicts']+conf
        newGraphState['notConflicts'] = self.graphState['notConflicts']+nonConf
        newGraphState['unknown'] = self.graphState['unknown']+unknown
        
        return newGraphState


'-----------------test util functions start--------------------'    
def createKnownGraph(graph, knownNodes):
    knownGraph = copy.deepcopy(graph)
    for node,data in graph.nodes(data = True):
        if node not in knownNodes:
            knownGraph.node[node]['color'] = -1
    return knownGraph
'-----------------test util functions end--------------------'
if __name__ == '__main__':
    
    t = ['a','b','c']
    for tt in t:
        print tt
        shuffle(t)
        
    a = 1/0
    
    l = {}
    if isinstance(l, dict):
        print 'yay'
    G=nx.Graph()
    colors = [0,1,2] # 0 = blue, 1 = red, 2 = green (unknown = black)
    possibleColorValues = [-1,0,1,2]
    
    blueNodes = []
    redNodes = []
    greenNodes = []
    unknownNodes = []
    nodeLabels = {}
    controlledNodes = []
    knownNodes = []
    
    numEdges = 0
    
    conf = 0
    nonConf = 0
    unknown = 0
    
    for n in range(0,12):
        col = random.choice(possibleColorValues)
        G.add_node(n, color = col)
#        print 'node: '+str(G.node[n])
        if col == -1:
            unknownNodes.append(n)
        elif col == 0:
            blueNodes.append(n)
        elif col == 1:
            redNodes.append(n) 
        elif col == 2:
            greenNodes.append(n)  
        nodeLabels[n] = n
        if random.random() < 0.3:
            controlledNodes.append(n)
        if random.random() < 0.4:
            knownNodes.append(n)
                     
        
    for i in range(0,len(G.nodes())):
        for j in range(i+1,len(G.nodes())):
            if (random.random()<0.6):
                G.add_edge(i,j)
                numEdges = numEdges +1
            
                if ((G.node[i]['color'] == -1) |  (G.node[j]['color'] ==-1)):
                    unknown = unknown + 1
                elif G.node[i]['color'] == G.node[j]['color']:
                    conf = conf +1
                elif G.node[i]['color'] != G.node[j]['color']:
                    nonConf = nonConf+1
            
    
    
    knownGraph = createKnownGraph(G, knownNodes)
    
    

    
    agt = Agent(1, controlledNodes, knownGraph, colors, 2)
    
    print 'controlledNodes: '
    print controlledNodes
    print 'knownNodes:'
    print knownNodes
    
    print 'computed conflicts:'
    print agt.graphState
    
    print 'true conflicts: '
    print 'conflicts : '+str(conf)+", unknown: "+str(unknown) +", notConflicts: "+str(nonConf)
    
    print 'numEdges = ' + str(len(G.edges()))
    
    acts = agt.chooseActions()
    for i,j in acts:
        print i
        print j
    #test update belief
#    newKnownNodes = {}
#    for i in range(0,3):
#        newKnownNodes[i] =G.node[i]['color']
#    
#    agt.updateBelief(newKnownNodes)
#    
#    newKnownNodes = {}
#    for i in range(0,2):
#        newKnownNodes[i] =G.node[i]['color']
#    
#    agt.updateBelief(newKnownNodes) 
    

#    print 'clustering'
#    print(nx.average_clustering(mip.mip, weight = "weight"))
#    #    G=nx.dodecahedral_graph()

    
    