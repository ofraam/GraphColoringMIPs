'''
Created on Jun 7, 2015

@author: Ofra
'''
import networkx
import math
import copy

class Agent:
    def __init__(self, id, subgraph, knownGraph, colors, actionLimit = 3):
        self.id = id
        self.controlledNodes = subgraph
        self.knownGraph = knownGraph
        self.actionLimit = actionLimit #number of change color actions allowed per round
        self.colors = colors #possible colors 
        #the graph sent by simulation has the colors, need to remove them for each agent
        for node, data in self.knownGraph.nodes(data = True):
            data['color']= -1
            data['uptoDate']= False
        
    #the function updates the agents' knowledge about the graph
    #nodesColorsList is a dict of node_id and current color
    def updateBelief(self, nodesColorsList):
        for node,color in nodesColorsList.iteritems():
            self.knownGraph[node]['color'] = color
            self.knownGraph[node]['uptoDate'] = True
    
    #chooses the color changes made by the agent.
    #limit is the maximum number of nodes that the agent is allowed to change in one round
    def chooseActions(self):
        newColors = {}
        #TODO: function that finds best set of changes to nodes
        
        
        return newColors;
    
    def chooseActionsRecur(self, actionSet, numConflicts, nodeCounter, bestSolution):
        #stop condition - when we reached the limit of actions permitted, or when reached the last node we can change
        if ((len(actionSet) == self.actionLimit) | (nodeCounter == len(self.controlledNodes))):
            if numConflicts < bestSolution['conflicts']: 
                bestSolution['actionSet']=actionSet
                bestSolution['conflicts']=numConflicts
            return
        else:
            #call function with all possible options for next node (not change, change to each of the colors that differ from the current color)
            self.chooseActionsRecur(self, actionSet,numConflicts,nodeCounter+1,bestSolution) #don't include a change to this node in action set
            for color in self.colors:
                if color != self.knownGraph[self.controlledNodes[nodeCounter]]['color']:
                    newActionSet = copy.deepcopy(actionSet)
                    newActionSet.append((nodeCounter,color))
                    newNumConflicts = self.computeNumConflicts(newActionSet)
                    if newNumConflicts>bestSolution['conflicts']:
                        continue;
                    else:
                        self.chooseActionsRecur(self, newActionSet,newNumConflicts,nodeCounter+1,bestSolution) #call function to check this action set
                        
        return;
                    
                    
    def computeNumConflicts(self,actionSet): #TODO: implement
        
        pass
                
             
    
        

if __name__ == '__main__':
    pass