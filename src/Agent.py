'''
Created on Jun 7, 2015

@author: Ofra
'''
import networkx
import math
import copy

class Agent:
    def __init__(self, id, subgraph, knownGraph, colors, actionLimit):
        self.id = id
        self.controlledNodes = subgraph
        self.knownGraph = knownGraph
        self.actionLimit = actionLimit #number of change color actions allowed per round
        self.colors = colors #possible colors 
        #the graph sent by simulation has the colors, need to remove them for each agent
        for node, data in self.knownGraph.nodes(data = True):
            data['color']= -1
            data['uptoDate']= False
        
        self.graphState = {}; #will hold current known numbers for 'conflicts' 'notConflicts' and 'unknown'
        self.countNumConflicts()
        
    #count initial number of conflicts
    def countNumConflicts(self):
        #counters of updates to conflicts
        unknown = 0
        conf = 0
        nonConf = 0 
        for u,v in self.graph.edges_iter():
            colU = self.graph.node[u]['color']
            colV = self.graph.node[v]['color']
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
            self.knownGraph[node]['color'] = color
            self.knownGraph[node]['uptoDate'] = True
            
        self.countNumConflicts() #update conflict counts
        return 
    
    #chooses the color changes made by the agent.
    #limit is the maximum number of nodes that the agent is allowed to change in one round
    def chooseActions(self):
        newColors = {}
        #TODO: function that finds best set of changes to nodes
        
        
        return newColors;
    
    def chooseActionsRecur(self, currSolution, nodeCounter, bestSolution):
        #TODO: add caching of partial action sets as to not recompute stuff?
        #stop condition - when we reached the limit of actions permitted, or when reached the last node we can change
        if ((len(currSolution['actionSet']) == self.actionLimit) | (nodeCounter == len(self.controlledNodes))):
            if currSolution['conflicts'] < bestSolution['conflicts']: 
                bestSolution=currSolution
            #break ties in favor of more known non-conflicts (otherwise might bias towards doing nothing)   
            elif currSolution['conflicts'] == bestSolution['conflicts']:
                if currSolution['notConflicts'] > bestSolution['notConflicts']:
                    bestSolution=currSolution
            return
        else:
            #call function with all possible options for next node (not change, change to each of the colors that differ from the current color)
            self.chooseActionsRecur(self, currSolution,nodeCounter+1,bestSolution) #don't include a change to this node in action set
            
            for color in self.colors: #change current node and recall function with each option
                if color != self.knownGraph[self.controlledNodes[nodeCounter]]['color']: #don't try the same color, that is equivalent to no action so should not "waste" real action on that
                    newActionSet = copy.deepcopy(currSolution['actionSet'])
                    newActionSet.append((self.controlledNodes[nodeCounter],color))
                    newGraphState = self.computeNumConflicts(newActionSet)
                    if newGraphState['conflicts']>bestSolution['conflicts']:
                        continue;

                    else:
                        newSolution = {}
                        newSolution['actionSet'] = newActionSet
                        newSolution['conflicts'] = newGraphState['conflicts']
                        newSolution['notConflicts'] = newGraphState['notConflicts']
                        newSolution['unknown'] = newGraphState['unknown']
                        self.chooseActionsRecur(self, newSolution,nodeCounter+1,bestSolution) #call function to check this action set                  
                    
                        
        return;
                    
                    
    def computeNumConflicts(self,actionSet): #TODO: test
        newGraphState = {} #dictionary with 'conflicts' 'notConflicts' and 'unknown'
        prevColors = {} #store previous colors to check changed conflicts
        #counters of updates to conflicts
        unknown = 0
        conf = 0
        nonConf = 0 
        pairsOfChanged = [] #will hold list of edges for which both nodes changed in current action set
        changedNodes = [actionSet[i][0] for i in range(len(actionSet))]
        
        for action in actionSet:
            prevColors[action[0]] = self.knownGraph[action[0]]['color'] #saving old color to see if conflicts changed
            #re-checking all neighbors of node that changed, except neighbors that include another changed node (will check them next)
            for n in self.knownGraph.neighbors(action[0]):
                node = self.knownGraph.node[n] #get data for node (for color)
                if node not in changedNodes:
                    if self.knownGraph[node]['color']!=-1: #if the neighbor is uncolored, we move from unknown-> unknown which is not going to make any difference. 
                        if action[1]!=self.knownGraph[node]['color']: #there is currently no conflict (and that is not because the neighboring node is not colored) 
                            if ((action[1]!=prevColors[action[0]]) & (prevColors[action[0]]==-1)): #unknown --> not conflict
                                unknown = unknown -1
                                nonConf = nonConf +1
                            else: #there was previously a conflict: conf --> nonConf
                                nonConf = nonConf+1
                                conf = conf -1
                        else: #we have a conflict! 
                            if prevColors[action[0]] == -1: #unknown --> conf
                                unknown = unknown - 1
                                conf = conf + 1
                            else: #noConf-->conf
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
        
if __name__ == '__main__':
 
    l = []
    l.append((1,2))
    l.append((3,3))
    l.append((4,5))
    a = [l[i][0] for i in range(len(l))]
#    newList = [[each_list[i] for i in list1] for each_list in list2]
    for i,j in l:
        print i
        print j
#    print l[:][0]
    pass