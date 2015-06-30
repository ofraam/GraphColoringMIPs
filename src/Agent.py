'''
Created on Jun 7, 2015

@author: Ofra
'''
import networkx as nx
import math
import copy
import random
import matplotlib.pyplot as plt

class Agent:
    def __init__(self, id, subgraph, knownGraph, colors, actionLimit):
        self.id = id
        self.controlledNodes = subgraph
        self.knownGraph = knownGraph
        self.actionLimit = actionLimit #number of change color actions allowed per round
        self.colors = colors #possible colors 
        #the graph sent by simulation has the colors, need to remove them for each agent
        for node, data in self.knownGraph.nodes(data = True):
#            data['color']= -1 #TODO: bring back to initialize!
            data['uptoDate']= False
        
        self.graphState = {}; #will hold current known numbers for 'conflicts' 'notConflicts' and 'unknown'
        self.countNumConflicts()
        
    #count initial number of conflicts
    def countNumConflicts(self):
        #counters of updates to conflicts
        unknown = 0
        conf = 0
        nonConf = 0 
        for u,v in self.knownGraph.edges_iter():
#            print 'u = '+str(u) + ", v = "+str(v)
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
    def updateBelief(self, nodesColorsList):
        #reset old stuff
        for node, data in self.knownGraph.nodes(data = True):
            if data['uptoDate']== True: # if node was uptoDate in the last turn, treat the color unchanged but reset uptoDate so next turn it gets reset
                data['uptoDate']= False
            else: #the node is not uptodate, reset the color to unknown
                data['color'] = -1
        
        #update new stuff
        for node,color in nodesColorsList.iteritems():
            self.knownGraph.node[node]['color'] = color
            self.knownGraph.node[node]['uptoDate'] = True
            
        self.countNumConflicts() #update conflict counts
        return 
    
    #chooses the color changes made by the agent.
    #limit is the maximum number of nodes that the agent is allowed to change in one round
    def chooseActions(self):
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
        
        bestSolution = self.chooseActionsRecur(initialSolution,0,initialBestSolution)
        
        return bestSolution['actionSet'];
    
    def chooseActionsRecur(self, currSolution, nodeCounter, bestSolution):
        #TODO: add caching of partial action sets as to not recompute stuff?
        #stop condition - when we reached the limit of actions permitted, or when reached the last node we can change
        if ((len(currSolution['actionSet']) == self.actionLimit) | (nodeCounter == len(self.controlledNodes))):
            if currSolution['conflicts'] < bestSolution['conflicts']: 
                print 'oldBest: '+str(bestSolution)
                
                bestSolution=currSolution
                print 'newBest: '+str(bestSolution)
                
            #break ties in favor of more known non-conflicts (otherwise might bias towards doing nothing)   
            elif currSolution['conflicts'] == bestSolution['conflicts']:
                if currSolution['notConflicts'] > bestSolution['notConflicts']:
                    bestSolution=currSolution
            return bestSolution
        else:
            #call function with all possible options for next node (not change, change to each of the colors that differ from the current color)
            
            
            for color in self.colors: #change current node and recall function with each option
                if color != self.knownGraph.node[self.controlledNodes[nodeCounter]]['color']: #don't try the same color, that is equivalent to no action so should not "waste" real action on that
                    newActionSet = copy.deepcopy(currSolution['actionSet'])
                    newActionSet.append((self.controlledNodes[nodeCounter],color))
                    newGraphState = self.computeNumConflicts(newActionSet)

                    if newGraphState['conflicts']>bestSolution['conflicts']:
                        print 'pruned: '+str(newActionSet)
                        print 'best solution = '+str(bestSolution)
                        print 'newGraphState = '+str(newGraphState)
                        continue;

                    else:
                        newSolution = {}
                        newSolution['actionSet'] = newActionSet
                        newSolution['conflicts'] = newGraphState['conflicts']
                        newSolution['notConflicts'] = newGraphState['notConflicts']
                        newSolution['unknown'] = newGraphState['unknown']
                        bestSolution = self.chooseActionsRecur(newSolution,nodeCounter+1,bestSolution) #call function to check this action set                  
            
            bestSolution = self.chooseActionsRecur(currSolution,nodeCounter+1,bestSolution) #don't include a change to this node in action set
                        
        return bestSolution;
                    
                    
    def computeNumConflicts(self,actionSet): #TODO: test

        newGraphState = {} #dictionary with 'conflicts' 'notConflicts' and 'unknown'
        prevColors = {} #store previous colors to check changed conflicts
        #counters of updates to conflicts
        unknown = 0
        conf = 0
        nonConf = 0 
        print actionSet
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
            #re-checking all neighbors of node that changed, except neighbors that include another changed node (will check them next)
            for n in self.knownGraph.neighbors(action[0]):
                node = self.knownGraph.node[n] #get data for node (for color)
                if node not in changedNodes:
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
            node1 = self.knownGraph.node[n1]
            node2 = self.knownGraph.node[n2]
            if node1['color'] != node2['color']: #currently, no conflict; could be no->no (nothing to do), yes->no or unknown->no
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
        print 'node: '+str(G.node[n])
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
    
    agt.chooseActions()
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
    
    pos = nx.spring_layout(G)
    nx.draw_networkx_nodes(G,pos,nodelist=blueNodes,node_size=300,node_color='blue')
    nx.draw_networkx_nodes(G,pos,nodelist=redNodes,node_size=300,node_color='red')
    nx.draw_networkx_nodes(G,pos,nodelist=greenNodes,node_size=300,node_color='green')
    nx.draw_networkx_nodes(G,pos,nodelist=unknownNodes,node_size=300,node_color='black')
#    nx.draw_networkx_nodes(mip.mip,pos,nodelist=parNodes,node_size=300,node_color='blue')
#    nx.draw_networkx_nodes(mip.mip,pos,nodelist=parDeletedNodes, node_size=300,node_color='black')
    nx.draw_networkx_edges(G,pos,edgelist=G.edges())
    nx.draw_networkx_labels(G,pos,labels = nodeLabels, font_color = "white")
#    print 'clustering'
#    print(nx.average_clustering(mip.mip, weight = "weight"))
#    #    G=nx.dodecahedral_graph()
##    nx.draw(mip.mip)
    plt.draw()
##    plt.savefig('ego_graph50.png')
    plt.show()
    
    