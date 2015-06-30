'''
Created on Jun 7, 2015

@author: Ofra
'''

import networkx as nx
import math

class GraphProblem:
    def __init__(self, graphObj, colors):
        self.graph = graphObj
        self.colors = colors
        for node in self.graph.nodes(data=True): #initialize all colors to -1 (color not set yet)
            node['color'] = -1
        
    def getColor(self, node):
        return self.graph.node[node]['color']
    
    def changeColor(self, node, newColor):
        self.graph.node[node]['color'] = newColor
        
    def getAllConflicts(self): 
        conflicts = []
        for u,v in self.graph.edges_iter():
            if self.graph.node[u]['color']==self.graph.node[v]['color']: #TODO: consider case of undetermined colors!
                conflicts.append((u,v)) #TODO: check if this is the right thing or need the edge obj itself
        return conflicts
    
    def getConflictsForNodes(self,nodesList):
        conflicts = []
        for edge in nx.edges(self.graph, nodesList):
            if self.graph.node[edge[0]]['color']==self.graph.node[edge[0]]['color']:
                conflicts.append(edge)
                
    def getNodesSubgraph(self,nodesList):
        return nx.edges(self.graph, nodesList)
        
if __name__ == '__main__':
    G=nx.Graph()
    G.add_edge(1,2)  # default edge data=1
    G.add_edge(2,3,weight=0.9) # specify edge data
    nbunch = []
    nbunch.append(2)
    e = nx.edges(G,nbunch)
    print e[0]
    a = (2,1)
    print a
    print e[0] == a
    pass