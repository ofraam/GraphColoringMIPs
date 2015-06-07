'''
Created on Jun 7, 2015

@author: Ofra
'''
import networkx as nx
import math

class Session:
    def __init__(self, user, revision, time):
        self.actions = []
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
        

class Mip:
    def __init__(self):
        self.mip = nx.Graph()
        self.aos = {}
        self.users = {}
        self.iteration = 0
        self.lastID = 0
        self.decay = 0.01
        self.sigIncrement = 1
        self.minIncrement = 0.1
        self.current_flow_betweeness = None #centrality values of all nodes
        self.log = [] #log holds all the session data 
              
                
    def updateMIP(self, session):
        #initialize 'updated' attribute of all edges to false
        for edge in self.mip.edges_iter(data=True):
            edge[2]['updated']=0
            
        self.log.append(session) #append session to log
        user = session.user
        if (user not in self.users):
            self.addUser(user)
        user_node = self.users[user]
        #update MIP based on all actions
        for act in session.actions:
            ao = act.ao
            if (ao not in self.objects):
                nodeIdInMip = self.addObject(ao)
                act.updateMipNodeID(nodeIdInMip)
            ao_node = self.objects[ao]
            self.updateEdge(user_node, ao_node, 'u-ao', act.weightInc)
            #label deleted objects as deleted
            if act.actType == 'delete':
                self.mip.node[self.objects[act.ao]]['deleted'] = 1
        
        for i in range(len(session.actions)):
            ao_node1 = self.objects[session.actions[i].ao]
            for j in range(i+1, len(session.actions)):
                ao_node2 = self.objects[session.actions[j].ao]
            if (ao_node1!=ao_node2):
                self.updateEdge(ao_node1, ao_node2, 'ao-ao', self.objectsInc)
        
        #TODO: think about adding decay here!!
        
        self.currentSession=session
#        print'updating'

        try:
            self.current_flow_betweeness = nx.current_flow_betweenness_centrality(self.mip,True, weight = 'weight')
        except:
            self.current_flow_betweeness = nx.degree_centrality(self.mip)
        
    def addUser(self,user_name):
        if (user_name in self.users):
            return self.users[user_name]
        else:
            self.lastID=self.lastID+1
            self.users[user_name] = self.lastID
            attr = {}
            attr['type']='user'
            self.mip.add_node(self.lastID, attr)
            self.nodeIdsToUsers[self.lastID]=user_name
        return self.users[user_name]
            
    
    def addObject(self, object_id):
        if (object_id in self.objects):
            return self.objects[object_id]
        else:
            self.lastID=self.lastID+1
            self.objects[object_id] = self.lastID
            attr = {}
            attr['type']='object'
            self.mip.add_node(self.lastID, attr)
            self.nodeIdsToObjects[self.lastID]=object_id
        return self.objects[object_id]
        
           
    def updateEdge(self,i1,i2,edge_type,increment = 1):
        if self.mip.has_edge(i1, i2):
            self.mip[i1][i2]['weight']=self.mip[i1][i2]['weight']+increment
        else:
            attr = {}
            attr['type']=type
            attr['weight']=increment
            self.mip.add_edge(i1, i2, attr)
        self.mip[i1][i2]['updated']=1
        
    def getLiveObjects(self):
        liveObjects = []
        for node in self.mip.nodes(True):
            if node[1]['type']=='par':
                if node[1]['deleted']==0:
                    liveObjects.append(node)
        return liveObjects
    
    def getLiveAos(self):
        liveObjects = []
        for node in self.mip.nodes(True):
            if node[1]['type']=='par':
                if node[1]['deleted']==0:
                    liveObjects.append(node[0])
        return liveObjects
    '''
    -----------------------------------------------------------------------------
    MIPs reasoning functions start
    -----------------------------------------------------------------------------
    '''
    def DegreeOfInterestMIPs(self, user, obj, current_flow_betweeness, alpha=0.3, beta=0.7, similarity = "adamic"):
     
        api_obj = current_flow_betweeness[obj]  #node centrality
    #    print 'obj'
    #    print obj
    #    print 'api_obj'
    #    print api_obj
       
        #compute proximity between user node and object node using Cycle-Free-Edge-Conductance from Koren et al. 2007 or Adamic/Adar
        proximity = 0
        if ((user in self.users) & (beta>0)): #no point to compute proximity if beta is 0... (no weight)
            userID = self.users[user]
            if similarity == "adamic":
                proximity = self.adamicAdarProximity(userID,obj) #Adamic/Adar proximity
#                print 'computing proximity'
            else:
                proximity = self.CFEC(userID,obj) #cfec proximity
        else:
            return alpha*api_obj
#        print 'api_obj = '+str(api_obj)
#        print 'proximity = '+str(proximity)
        return alpha*api_obj+beta*proximity #TODO: check that scales work out for centrality and proximity, otherwise need some normalization


    '''
    computes Adamic/Adar proximity between nodes, adjusted to consider edge weights
    here's adamic/adar implementation in networkx. Modifying to consider edge weights            
    def predict(u, v):
        return sum(1 / math.log(G.degree(w))
                   for w in nx.common_neighbors(G, u, v))
    '''


    def adamicAdarProximity(self, s, t):
        proximity = 0.0
        for node in nx.common_neighbors(self.mip, s, t):
            weights = self.mip[s][node]['weight'] + self.mip[t][node]['weight'] #the weight of the path connecting s and t through the current node
            if weights!=0: #0 essentially means no connection
#                print 'weights = '+str(weights)
#                print 'degree = '+str(self.mip.degree(node, weight = 'weight'))
                proximity = proximity + (weights*(1/(math.log(self.mip.degree(node, weight = 'weight'))+0.00000000000000000000000001))) #gives more weight to "rare" shared neighbors, adding small number to avoid dividing by zero
#                print 'proximity = '+str(proximity)
        return proximity    
    '''
    computes Cycle-Free-Edge-Conductance from Koren et al. 2007
    for each simple path, we compute the path probability (based on weights) 
    '''
    def CFEC(self,s,t):
        R = nx.all_simple_paths(self.mip, s, t, cutoff=3)
        proximity = 0.0
        for r in R:
            PathWeight = self.mip.degree(r[0])*(self.PathProb(r))  #check whether the degree makes a difference, or is it the same for all paths??
            proximity = proximity + PathWeight
            
            
        return proximity
        
            
    def PathProb(self, path):
        prob = 1.0
        for i in range(len(path)-1):
            prob = prob*(float(self.mip[path[i]][path[i+1]]['weight'])/self.mip.degree(path[i]))
#        print 'prob' + str(prob)
        return prob
    
    '''
    rank all live objects based on DOI to predict what edits a user will make.
    NOTE: need to call this function with the mip prior to the users' edits!!!
    '''
    def rankLiveObjectsForUser(self, user, alpha = 0.3, beta = 0.7, similarity = "adamic"):
        aoList = self.getLiveAos()
#        print 'number of aos = '+str(len(aoList))
        notificationsList = []
        for ao in aoList:
            doi = self.DegreeOfInterestMIPs(user, ao,self.current_flow_betweeness, alpha, beta, similarity)  
            
            if len(notificationsList)==0:
                toAdd = []
                toAdd.append(ao)
                toAdd.append(doi)
                notificationsList.append(toAdd)
            else:
                j = 0
                while ((doi<notificationsList[j][1])):
                    if j<len(notificationsList)-1:
                        j = j+1
                    else:
                        j=j+1
                        break
                toAdd = []
                toAdd.append(ao)
                toAdd.append(doi)                  
                if (j<len(notificationsList)):
                    notificationsList.insert(j, toAdd)
                else:
                    notificationsList.append(toAdd)  
#        print 'notification list size = '+str(len(notificationsList))        
        return notificationsList
    
    def rankChangesForUser(self,user,time, onlySig = True, alpha = 0.3, beta = 0.7, similarity = "adamic"):
        notificationsList = []
        checkedObjects = {}
        for i in range(time, len(self.log)-1): #this includes revision at time TIME and does not include last revision in MIP, which is the one when the user is back 
#            print "time = "+str(i) + "author = "+self.log[i].user
                        
            session = self.log[i]
            for act in session.actions: 

                if ((act.actType != 'smallEdit') | (onlySig == False)):
                    if (act.ao not in checkedObjects): #currently not giving more weight to the fact that an object was changed multiple times. --> removed because if there are both big and small changes etc...
                        #TODO: possibly add check whether the action is notifiable
                        
                        doi = self.DegreeOfInterestMIPs(user, act.ao,self.current_flow_betweeness, alpha, beta, similarity)
                        checkedObjects[act.ao] = doi
                    else:
                        doi = checkedObjects[act.ao] #already computed doi, don't recompute!
                    #put in appropriate place in list based on doi
                    if len(notificationsList)==0:
                        toAdd = []
                        toAdd.append(act)
                        toAdd.append(doi)
                        notificationsList.append(toAdd)
                    else:
                        j = 0

                        while ((doi<notificationsList[j][1])):
                            if j<len(notificationsList)-1:
                                j = j+1
                            else:
                                j=j+1
                                break
                        toAdd = []
                        toAdd.append(act)
                        toAdd.append(doi)   
                     
                        if (j<len(notificationsList)):
                            notificationsList.insert(j, toAdd)
                        else:
                            notificationsList.append(toAdd)                        
        return notificationsList
    
    def rankChangesGivenUserFocus(self,user,focus_obj, time):
        notificationsList = []
        checkedObjects = []
        for i in range(time, len(self.log)-1):
            session = self.log[i]
            for act in session.actions:
                if (act.ao not in checkedObjects):
                    #TODO: possibly add check whether the action is notifiable
                    doi = self.DegreeOfInterestMIPs(focus_obj, act.ao)
                    #put in appropriate place in list based on doi
                    if (len(notificationsList==0)):
                        notificationsList.append(act.ao, doi)
                    else:
                        j = 0
                        while (doi<notificationsList[j][1]):
                            j = j+1
                        notificationsList.insert(j, act.ao)
                        
        return notificationsList

             
                
    '''
    -----------------------------------------------------------------------------
    MIPs reasoning functions end
    -----------------------------------------------------------------------------
    '''


if __name__ == '__main__':
    pass