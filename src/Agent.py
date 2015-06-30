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
    
    #chooses the color changes made by the agent.
    #limit is the maximum number of nodes that the agent is allowed to change in one round
    def chooseActions(self):
        newColors = {}
        #TODO: function that finds best set of changes to nodes
        
        
        return newColors;
    
    def chooseActionsRecur(self, currSolution, nodeCounter, bestSolution):
        #TODO: add caching of partial action sets as to not recompute stuff...
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
            for color in self.colors:
                if color != self.knownGraph[self.controlledNodes[nodeCounter]]['color']:
                    newActionSet = copy.deepcopy(currSolution['actionSet'])
                    newActionSet.append((nodeCounter,color))
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
                    
                    
    def computeNumConflicts(self,actionSet): #TODO: implement; return dictionary with 'conflicts' 'notConflicts' and 'unknown'
        prevColors = {}
        for action in actionSet:
            
        
        pass
                
             
    
        

if __name__ == '__main__':
    pass