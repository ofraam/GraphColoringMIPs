'''
Created on Jun 11, 2015

@author: Ofra
'''


class Session:
    def __init__(self, user, revision, time): 
        self.actions = revision
        self.user = user 
        self.time = time
        
    def __str__(self):
        toPrint = "session at time "+str(self.time) +" user = "+str(self.user)+"\n"
        for act in self.actions:
            toPrint = toPrint+str(act)+"\n"
        return toPrint
        
class Action:
    def __init__(self, user, ao, actType, desc, weightInc, changeExtent):
        self.user = user
        self.ao = ao
        self.actType = actType #view, edit, add, delete
        self.desc = desc
        self.weightInc = weightInc
        self.mipNodeID = -1
        self.changeExtent = changeExtent
        
        
    def updateMipNodeID(self, id):
        self.mipNodeID = id
        
    def __str__(self):
        return "user = "+str(self.user) +"\n"+"ao = "+str(self.ao) +"\n" + "actType = "+self.actType +"\n" + "desc = "+self.desc +"\n" + "weightInc = "+str(self.weightInc) +"\n" + "extent of change = "+str(self.changeExtent) +"\n" + "mipNodeID = "+str(self.mipNodeID) +"\n"

class Result:        
    def __init__(self, system, numIterations, graphState, percentColored):
        self.system = system
        self.iterations = numIterations
        self.graphState = graphState
        self.colored = percentColored
        
    def __str__(self):
        return "system = "+str(self.system) +"\n"+"iterations = "+str(self.iterations) +"\n" + "graph state = "+str(self.graphState) +"\n" + "percent colored = "+str(self.percentColored) +"\n"
if __name__ == '__main__':
    pass