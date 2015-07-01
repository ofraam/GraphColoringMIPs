'''
Created on Jul 1, 2015

@author: Ofra
'''
import random
import operator 

class RandomSystem:
    def __init__(self):
        self.nodes = []
        
    
    def update(self, session):
        for act in session:
            if act.ao not in self.nodes:
                self.nodes.append(act.ao)
        
    
    def query(self, infoLimit):
        nodesToShare = random.choice(self.nodes,infoLimit)
        return nodesToShare
    
class MostChangedSystem:
    def __init__(self):
        self.nodeChangeCounts = {}
        
    def update(self, session):
        for act in session:
            if act.ao in self.nodeChangeCounts.keys():
                prevHits = self.nodeChangeCounts[act.ao]  
                self.nodeChangeCounts[act.ao] = prevHits+1
            else:
                self.nodeChangeCounts[act.ao]=1
                
    
    def query(self, infoLimit):
        sorted_dict = sorted(self.nodeChangeCounts.items(), key=operator.itemgetter(1), reverse = True)
        rankedNodes = [sorted_dict[i][0] for i in range(len(sorted_dict))]
        nodesToShare = rankedNodes[:infoLimit]
        return nodesToShare 
    
class MostChangedInIntervalSystem:
    def __init__(self, timeWindow):
        self.nodeChangetimes = {}
        self.nodeChangeCount = {}
        self.window = timeWindow
        
    def update(self, session):
        for act in session:
            if act.ao in self.nodeChangetimes.keys():
                self.nodeChangetimes[act.ao].append(session.time)  
                timeList = self.nodeChangetimes[act.ao]
                lastRevToConsider = max(0,session.time-self.window)
                i = 0
                while timeList[i]< lastRevToConsider:
                    i = i+1
                if i<len(timeList):
                    timeList = timeList[i:]     
                self.nodeChangeCount[act.ao] = len(timeList)           
                
            else:
                self.nodeChangetimes[act.ao] = []
                self.nodeChangetimes[act.ao].append(session.time)
                self.nodeChangeCount[act.ao] = 1


            
    def query(self, infoLimit):
        sorted_dict = sorted(self.nodeChangeCount.items(), key=len(operator.itemgetter(1)), reverse = True)
        rankedNodes = [sorted_dict[i][0] for i in range(len(sorted_dict))]
        nodesToShare = rankedNodes[:infoLimit]
        return nodesToShare     
    
class LatestChangedSystem:
    def __init__(self):
        self.nodeChangetimes = {}
        
    def update(self, session):
        for act in session:
            self.nodeChangetimes[act.ao] = session.time
                
    def query(self, infoLimit):
        sorted_dict = sorted(self.nodeChangetimes.items(), key=operator.itemgetter(1), reverse = True)
        rankedNodes = [sorted_dict[i][0] for i in range(len(sorted_dict))]
        nodesToShare = rankedNodes[:infoLimit]
        return nodesToShare           
        
if __name__ == '__main__':
    l = [1,2,3,4]
    l = l[:2]
    print l
    pass