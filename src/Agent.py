'''
Created on Jun 7, 2015

@author: Ofra
'''
import networkx
import math

class Agent:
    def __init__(self, id, subgraph, knownGraph):
        self.id = id
        self.controlledNodes = subgraph
        self.knownGraph = knownGraph
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
    def chooseActions(self, limit = 1000):
        newColors = {}
        #TODO: function that finds best set of changes to nodes
        
        
        return newColors;
    
    
        

if __name__ == '__main__':
    pass