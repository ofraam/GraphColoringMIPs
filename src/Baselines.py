'''
Created on Jul 1, 2015

@author: Ofra
'''
import random
import operator 
from Utils import Session
from Utils import Action


class RandomSystem:
    def __init__(self):
        self.nodes = []
        
    
    def update(self, session):
        for act in session.actions:
            if act.ao not in self.nodes:
                self.nodes.append(act.ao)
        
    
    def query(self, agent, infoLimit):
        nodesToShare = random.sample(self.nodes,min(infoLimit,len(self.nodes)))
        return nodesToShare
    
    def __str__(self):
        return "Random"
        
class MostChangedSystem:
    def __init__(self):
        self.nodeChangeCounts = {}
        
    def update(self, session):
        for act in session.actions:
            if act.ao in self.nodeChangeCounts.keys():
                prevHits = self.nodeChangeCounts[act.ao]  
                self.nodeChangeCounts[act.ao] = prevHits+1
            else:
                self.nodeChangeCounts[act.ao]=1
                
    
    def query(self, agent, infoLimit):
        sorted_dict = sorted(self.nodeChangeCounts.items(), key=operator.itemgetter(1), reverse = True)
        rankedNodes = [sorted_dict[i][0] for i in range(len(sorted_dict))]
        nodesToShare = rankedNodes[:infoLimit]
        return nodesToShare 

    def __str__(self):
        return "MostChanged"
        
class MostChangedInIntervalSystem:
    def __init__(self, timeWindow):
        self.nodeChangetimes = {}
        self.nodeChangeCount = {}
        self.window = timeWindow
        
    def update(self, session):
        for act in session.actions:
            if act.ao in self.nodeChangetimes.keys():
                self.nodeChangetimes[act.ao].append(session.time)  
       
                
            else:
                self.nodeChangetimes[act.ao] = []
                self.nodeChangetimes[act.ao].append(session.time)
                self.nodeChangeCount[act.ao] = 1
                
            
        for node in self.nodeChangetimes:
            timeList = self.nodeChangetimes[node]
            lastRevToConsider = max(0,session.time-self.window)
            i = 0
            while ((i<len(timeList)) & (timeList[i]< lastRevToConsider)):
                i = i+1
                if i>=len(timeList)-1:
                    break;
            if i<len(timeList):
                timeList = timeList[i:]     
            else:
                timeList = []
            self.nodeChangeCount[node] = len(timeList)                    

            
    def query(self, agent, infoLimit):
        sorted_dict = sorted(self.nodeChangeCount.items(), key=operator.itemgetter(1), reverse = True)
        rankedNodes = [sorted_dict[i][0] for i in range(len(sorted_dict))]
        nodesToShare = rankedNodes[:infoLimit]
        return nodesToShare     
    
    def __str__(self):
        return "MostChangedInterval ("+str(self.window)+")"    
    
class LatestChangedSystem:
    def __init__(self):
        self.nodeChangetimes = {}
        
    def update(self, session):
        for act in session.actions:
            self.nodeChangetimes[act.ao] = session.time
                
    def query(self, agent, infoLimit):
        sorted_dict = sorted(self.nodeChangetimes.items(), key=operator.itemgetter(1), reverse = True)
        rankedNodes = [sorted_dict[i][0] for i in range(len(sorted_dict))]
        nodesToShare = rankedNodes[:infoLimit]
        return nodesToShare          

    def __str__(self):
        return "RecentChanges"     
        
if __name__ == '__main__':
    #objects: 1,2,3
    #users: 1,2,3
    #systems: all
    systems = []
    randSys = RandomSystem()
    mostChanged = MostChangedSystem()
    mostChangeInt = MostChangedInIntervalSystem(3)
    latestSys = LatestChangedSystem()
    systems.append(randSys)
    systems.append(mostChanged)
    systems.append(mostChangeInt)
    systems.append(latestSys)
    
    
    act1 = Action(1, 1, "sigEdit", "1", 1, 1)
    act2 = Action(1, 2, "sigEdit", "1", 1, 1)
    actions = []
    actions.append(act1)
    actions.append(act2)
    session = Session(1, actions, 1)
    
    for s in systems:
        s.update(session)
    
    act1 = Action(2, 1, "sigEdit", "1", 1, 1)
    act2 = Action(2, 3, "sigEdit", "1", 1, 1)
    actions = []
    actions.append(act1)
    actions.append(act2)
    session = Session(2, actions, 2) 
    
    for s in systems:
        s.update(session)
            
    act1 = Action(3, 3, "sigEdit", "1", 1, 1)
    act2 = Action(2, 2, "sigEdit", "1", 1, 1)
    actions = []
    actions.append(act1)
    actions.append(act2)
    session = Session(3, actions, 3)    
    
    for s in systems:
        s.update(session)
        acts = s.query(1,2)
        print 'system: '+str(s)
        print 'acts:'
        print acts  
        
    print 'done'  
    