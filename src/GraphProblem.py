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
#        for node,data in self.graph.nodes(data=True): #initialize all colors to -1 (color not set yet)
#            data['color'] = -1
        
    def updateGraph(self, changes):
        for node,col in changes:
            self.changeColor(node, col)
    
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
    
    def getConflictsForNodes(self,nodesList):#TODO: consider case where colors are not set yet
        conflicts = []
        for edge in nx.edges(self.graph, nodesList):
            if self.graph.node[edge[0]]['color']==self.graph.node[edge[0]]['color']:
                conflicts.append(edge)
                
    def getNodesSubgraph(self,nodesList):
        return nx.edges(self.graph, nodesList)
    
    def getPercentColored(self):
        coloredCounter = 0.0
        for node,data in self.graph.nodes(data = True):
            if data['color']!=-1:
                coloredCounter = coloredCounter + 1
        percentColored = coloredCounter/len(self.graph.nodes())
        return percentColored
    
    def getGraphState(self):
        graphState = {}
        #counters of updates to conflicts
        unknown = 0
        conf = 0
        nonConf = 0 
        for u,v in self.graph.edges_iter():
#            print 'u = '+str(u) + ", v = "+str(v)
            colU = self.graph.node[u]['color']
            colV = self.graph.node[v]['color']
#            print 'colU = '+ str(colU)+", colV = "+str(colV)
            if ((colU == -1) | (colV == -1)):
                unknown = unknown + 1
            elif colU == colV:
                conf = conf+1
            else:
                nonConf = nonConf + 1
                
        graphState['conflicts'] = conf
        graphState['notConflicts'] = nonConf
        graphState['unknown'] = unknown
        return graphState
    
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