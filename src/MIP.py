'''
Created on Jun 7, 2015

@author: Ofra
'''
import networkx as nx
import math

class Mip:
    def __init__(self, alpha = 0.3, beta = 0.7, gamma = 0.0, similarityMetric = "adamic", setting = "all"):
        self.mip = nx.Graph()
        self.users = {}
        self.objects  = {}
        self.iteration = 0
        self.lastID = 0
        self.decay = 0.1
        self.objectsInc = 1.0
        self.current_flow_betweeness = None #centrality values of all nodes
        self.log = [] #log holds all the session data 
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.similarityMetric = similarityMetric
        self.nodeIDsToObjectsIds = {}
        self.setting = setting #update only about changes or about all objects
    
    def update(self, session): #to fit System API
        self.updateMIP(session)
        
    def query(self, user, infoLimit, startRev = 0): #to fit System API
        if self.setting == "all": #choosing of all objects
            rankedObjects = self.rankObjectsForUser(user)
            nodesToShare = rankedObjects[:infoLimit]
            nodes = [i[0] for i in nodesToShare]
        else: #choosing only of changed objects
            rankedObjects = self.rankChangesForUser(user, startRev)
            nodesToShare = rankedObjects[:infoLimit]
            nodes = [i[0] for i in nodesToShare]            
        
        for node in nodes:
            self.updateEdge(self.users[user], self.objects[node], 'u-ao', 0) #update the latest revision when the user was informed about the object
        return nodes
                    
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
            self.mip.node[ao_node]['revisions'].append(self.iteration) #add revision
            self.updateEdge(user_node, ao_node, 'u-ao', act.weightInc)
            #label deleted objects as deleted
            if act.actType == 'delete':
                self.mip.node[self.objects[act.ao]]['deleted'] = 1
        
        for i in range(len(session.actions)-1):
            ao_node1 = self.objects[session.actions[i].ao]
            for j in range(i+1, len(session.actions)):
                ao_node2 = self.objects[session.actions[j].ao]
            if (ao_node1!=ao_node2):
                self.updateEdge(ao_node1, ao_node2, 'ao-ao', self.objectsInc)
                
        #update weights between objects that user was informed about and objects that changed
        for i in range(len(session.actions)-1):
            ao_node1 = self.objects[session.actions[i].ao]
            for j in range(j, len(session.info)):
                ao_node2 = session.info[j]
            if (ao_node1!=ao_node2):
                self.updateEdge(ao_node1, ao_node2, 'ao-ao', self.objectsInc)
                        
        #TODO: think about adding decay here!
#        for edge in self.mip.edges_iter(data=True):
#            if edge[2]['updated']==0:
#                if edge[2]['type']=='ao-ao':
#                    edge[2]['weight'] = edge[2]['weight']-self.decay
        self.currentSession=session
#        print'updating'

        self.current_flow_betweeness = nx.degree_centrality(self.mip) #TODO: apriori importance for now is simply degree, consider reverting to more complex option
#        try:
#            self.current_flow_betweeness = nx.current_flow_betweenness_centrality(self.mip,True, weight = 'weight')
#        except:
#            self.current_flow_betweeness = nx.degree_centrality(self.mip)
        
    def addUser(self,user_name):
        if (user_name in self.users):
            return self.users[user_name]
        else:
            self.lastID=self.lastID+1
            self.users[user_name] = self.lastID
            attr = {}
            attr['type']='user'
            self.mip.add_node(self.lastID, attr)
#            self.nodeIdsToUsers[self.lastID]=user_name
        return self.users[user_name]
            
    
    def addObject(self, object_id):
        if (object_id in self.objects):
            return self.objects[object_id]
        else:
            self.lastID=self.lastID+1
            self.objects[object_id] = self.lastID
            attr = {}
            attr['type']='object'
            attr['deleted'] = 0
            attr['revisions'] = []
            attr['revisions'].append(self.iteration)
            self.mip.add_node(self.lastID, attr)
            self.nodeIDsToObjectsIds[self.lastID]=object_id
        return self.objects[object_id]
        
           
    def updateEdge(self,i1,i2,edge_type,increment = 1):
        if self.mip.has_edge(i1, i2):
            self.mip[i1][i2]['weight']=self.mip[i1][i2]['weight']+increment
            self.mip[i1][i2]['lastKnown']=self.iteration #update last time user knew about object
        else:
            attr = {}
            attr['type']=type
            attr['weight']=increment
            attr['lastKnown']=self.iteration #update last time user knew about object
            self.mip.add_edge(i1, i2, attr)
        self.mip[i1][i2]['updated']=1
        
    
    def getLiveAos(self): #return the mip nodes that represent live object
        liveObjects = []
        for node in self.mip.nodes(data = True):
            if node[1]['type']=='object':
                if node[1]['deleted']==0:
                    liveObjects.append(node[0])
        return liveObjects
    '''
    -----------------------------------------------------------------------------
    MIPs reasoning functions start
    -----------------------------------------------------------------------------
    '''
   
    '''
    Computes degree of interest between a user and an object
    gets as input the user id (might not yet be represented in mip) and obj node from MIP (not id)
    '''
    def DegreeOfInterestMIPs(self, user, obj):
     
        api_obj = self.current_flow_betweeness[obj]  #node centrality (apriori component)
       
        #compute proximity between user node and object node using Cycle-Free-Edge-Conductance from Koren et al. 2007 or Adamic/Adar
        proximity = 0.0
        if ((user in self.users) & (self.beta>0)): #no point to compute proximity if beta is 0... (no weight)
            userNodeID = self.users[user]
            if self.similarityMetric == "adamic":
                proximity = self.adamicAdarProximity(userNodeID,obj) #Adamic/Adar proximity
            else:
                proximity = self.CFEC(userNodeID,obj) #cfec proximity
        
        changeExtent = 0.0
        if self.gamma > 0:#need to consider how frequently the object has been changed since user last known about it
            changeExtent = self.changeExtent(self.users[user], obj)


        return self.alpha*api_obj+self.beta*proximity+self.gamma*changeExtent  #TODO: check that scales work out, otherwise need some normalization


    '''
    computes Adamic/Adar proximity between nodes, adjusted to consider edge weights
    here's adamic/adar implementation in networkx. Modifying to consider edge weights            
    def predict(u, v):
        return sum(1 / math.log(G.degree(w))
                   for w in nx.common_neighbors(G, u, v))
    '''
    def adamicAdarProximity(self, s, t): #s and t are the mip node IDs, NOT user/obj ids
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
    computes the extent/frequency to which an object was changed since the last time the user was notified about it
    will be a component taken into account in degree of interest 
    '''
    def changeExtent(self, userNode, aoNode):
        fromRevision = 0 #in case user does not exist yet or has never known about this object, start from revision 0
        if self.mip.has_edge(userNode, aoNode):
            fromRevision = self.mip[userNode][aoNode]['lastKnown'] #get the last time the user knew what the value of the object was
        revs = self.mip[aoNode]['revisions']
        i = 0.0
        while revs[i]<fromRevision:
            i = i+1
        if i<len(revs):
            return (len(revs)-i)/(self.iteration-fromRevision)
        else:
            return 0
    '''
    rank all live objects based on DOI to predict what edits a user will make.
    NOTE: need to call this function with the mip prior to the users' edits!!!
    '''
    def rankObjectsForUser(self, user):
        aoList = self.getLiveAos() #gets the MIP NODES that represent live objects
        notificationsList = [] #will hold list of objects, eventually sorted by interest
        for ao in aoList:
            doi = self.DegreeOfInterestMIPs(user, ao,self.current_flow_betweeness)  
            
            if len(notificationsList)==0:
                toAdd = []
                toAdd.append(self.nodeIDsToObjectsIds[ao]) #need to get the true object id to return (external to mip)
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
                toAdd.append(self.nodeIDsToObjectsIds[ao]) #need to get the true object id to return (external to mip)
                toAdd.append(doi)                  
                if (j<len(notificationsList)):
                    notificationsList.insert(j, toAdd)
                else:
                    notificationsList.append(toAdd)  
#        print 'notification list size = '+str(len(notificationsList))        
        return notificationsList
        
    '''
    rank only objects that have changed since the last time the user interacted (based on DOI to predict what edits a user will make.)
    NOTE: need to call this function with the mip prior to the users' edits!!!
    '''    
    def rankChangesForUser(self,user,time, onlySig = True):
        notificationsList = []
        checkedObjects = {}
        for i in range(time, len(self.log)): #this includes revision at time TIME and does  include last revision in MIP as we are querying before we update
#            print "time = "+str(i) + "author = "+self.log[i].user
                        
            session = self.log[i]
            for act in session.actions: 

                if ((act.actType != 'smallEdit') | (onlySig == False)):
                    inNotificationList = False
                    if (act.ao not in checkedObjects): #currently not giving more weight to the fact that an object was changed multiple times. --> removed because if there are both big and small changes etc...
                        #TODO: possibly add check whether the action is notifiable
                        
                        doi = self.DegreeOfInterestMIPs(user, self.objects[act.ao],self.current_flow_betweeness)
                        checkedObjects[act.ao] = doi
                    else:
                        doi = checkedObjects[act.ao] #already computed doi, don't recompute!
                        inNotificationList = True
                    #put in appropriate place in list based on doi
                    if len(notificationsList)==0:
                        toAdd = []
                        toAdd.append(act.ao)
                        toAdd.append(doi)
                        notificationsList.append(toAdd)
                    elif inNotificationList==False: #only add to list if wasn't already there (doi does not change)
                        j = 0

                        while ((doi<notificationsList[j][1])):
                            if j<len(notificationsList)-1:
                                j = j+1
                            else:
                                j=j+1
                                break
                        toAdd = []
                        toAdd.append(act.ao)
                        toAdd.append(doi)   
                     
                        if (j<len(notificationsList)):
                            notificationsList.insert(j, toAdd)
                        else:
                            notificationsList.append(toAdd)                        
        return notificationsList
    
    
    def rankChangesGivenUserFocus(self,user,focus_obj, time): #TODO: check correctness and try at some point
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

    def __str__(self):
        return "MIP" 
                 
                
    '''
    -----------------------------------------------------------------------------
    MIPs reasoning functions end
    -----------------------------------------------------------------------------
    '''


if __name__ == '__main__':
    pass