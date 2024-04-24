import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.recoco import Timer
from pox.lib.revent.revent import EventMixin
from pox.lib.revent.revent import Event
from pox.lib.addresses import EthAddr
from pox.lib.packet.ethernet import ethernet
import pox.lib.packet as pkt
from pox.lib.packet.lldp import lldp
from pox.lib.util import dpidToStr

#Auxiliary Graph class to abstract the graph topology and compute shortest path
class Graph:

	def __init__(self):
		self.edges = [] 
	
	def add_edges_from(self, l):
		self.edges = l
		
	def nodes(self):
		n = []
		for e in self.edges:
			if e[0] not in n:
				n.append(e[0])
			elif e[1] not in n:
				n.append(e[1])
		return n
		
	def get_edges(self, node): 
		edges = []
		for n in self.nodes():
			if (node, n) in self.edges:
				edges.append((node, n))
			elif (n, node) in self.edges:
				edges.append((n, node))
		return edges
		
	def shortest_path(self, source, target):
		print("SRC IS: ", source)
		print("Target is: ", target)
		print("Edges are: ",self.edges)
		distances = {}
		for node in self.nodes():
			if node == source:
				distances[node] = 0
			else:
				distances[node] = float('inf')

		
		predecessors = {}

		
		visited = set()

		while visited != set(self.nodes()):
		   
			min_node = None
			min_distance = float('inf')
			for node in self.nodes():
				if node not in visited and distances[node] < min_distance:
					min_node = node
					min_distance = distances[node]

			if min_node is None:
				break

			visited.add(min_node)
			edges = self.get_edges(min_node)
			
		
			for edge in edges:
				neighbor = edge[1] if edge[0] == min_node else edge[0]
				new_distance = distances[min_node] + 1  
				if new_distance < distances[neighbor]:
					distances[neighbor] = new_distance
					predecessors[neighbor] = min_node
		print("Predecessors are: ",predecessors)
		
		shortest_path = []
		current_node = target
		while current_node != source:
			if current_node not in predecessors:
				return None 
			shortest_path.insert(0, current_node)
			current_node = predecessors[current_node]

		shortest_path.insert(0, source) 

		return shortest_path

		
		
				


class UserMobility:
	
	def __init__(self):
		self.marked_nodes = []
		core.openflow.addListeners(self)
		self.switches = None #keys are all switches with a "Ports" list as value the main attributes of these "ports" are the name (s1,s2,...)
		self.dpids = [] #list of all dpids
		self.links = [] #list of all link objects found by the other module
		self.connections = {} #key is dpid connection object is value
		self.graph = None #abstracted graph
		self.switch_MACs = None # dpid as key and list of (port, MAC) tuple of the switch
		
	def install_flow_rule(self, dpid, out_port, dl_addr, conn):
		msg = of.ofp_flow_mod()
		msg.priority = 50000
		match = of.ofp_match(dl_src = dl_addr)
		msg.match = match
		action = of.ofp_action_output(port=out_port) #redirect packet on out_port
		msg.actions.append(action)
		conn.send(msg)
		
	def sort_and_install(self, sp, event):
		for i in range(len(sp)-1):
				#sp[i] is the string name, get dpid of this and next node. The host is not explicitly present in the path
				name = sp[i]   #name of the current node in the path
				next = sp[i+1] #name of next node in the path
				
				#We inspect a linking of the type  prev <-> curr <-> next , where prev, curr and next are the nodes; the flow rules will be  installed on the curr node
				dpid_curr = None
				dpid_next = None
				dpid_prev = None
				
				port_out_to_prev = None #We also need the out_port for the current node to establish the rule for flow B->A and not just B->C, for nodes A prev, B current/start, C next
				
				#Get prev name and, if host, get mac
				if i-1 >= 0: 
					prev = sp[i-1]
					
				else:
					#prev is the host: we get the src mac as the host mac and we get port_out_to_prev as the port we received the packet from
					prev = "h"
					src_mac = event.parsed.src
					port_out_to_prev = event.port
					print(f"Host used has {src_mac} as MAC and {port_out_to_prev} as the in_port of the packet")
				
			
				#Extract dpids correspondant to the node names
				for dpid in self.dpids:
					for i in self.switches[dpid]:
						if i.port_no == 65534:
							if i.name == name:
								dpid_curr = dpid
						if i.port_no == 65534:
							if i.name == next:
								dpid_next = dpid 
						if i.port_no == 65534:
							if i.name == prev:
								dpid_prev = dpid
				dpid_curr_ = dpid_curr
				dpid_next_ = dpid_next
				dpid_curr = dpidToStr(dpid_curr)
				dpid_next = dpidToStr(dpid_next)
				if dpid_prev != None:
					dpid_prev = dpidToStr(dpid_prev)
				
				#Get the source MAC to match the rule and output port to redirect packet
				port_out = None
				port_prev = None
				dst_mac = None #we need dst mac to install the "reverse" rule cited just above
				for i in self.links:
					#We find the link between current and next node and get the port of the current node: scan curr <-> next 
					if (i.dpid1 == dpid_curr and i.dpid2 == dpid_next):
						#Get output port of current node
						port_out = i.port1
						#Get dst mac by scanning all macs of node  'next' and retrieving that of port2 of the curr<->next link
						for tup in self.switch_MACs[dpid_next]:
							if tup[0] == i.port2:
								dst_mac = tup[1]
								break

					#Scan prev <-> next link
					elif (i.dpid1 == dpid_prev and i.dpid2 == dpid_curr):
						#Get output port of previous node, where the packet came from
						port_prev = i.port1
						port_out_to_prev = i.port2
						#Get MAC of source when it's not host of prev interface
						for tup in self.switch_MACs[dpid_prev]:
							if tup[0] == port_prev:
								src_mac = tup[1]
								break
					
				#get curr connection
				conn = None
				for k in self.connections.keys():
					if k == dpid_curr_:
						conn = self.connections[dpid_curr_]
										
							
				#Should never happen				
				if src_mac == None or port_out == None or port_out_to_prev == None or conn == None:
					print("Error information not found!")
					exit(1)
					
				#Install flow rules for curr -> next and next -> curr packet exchange		 
				self.install_flow_rule(dpid_curr_, port_out, src_mac, conn) 
				self.install_flow_rule(dpid_next_, port_out_to_prev, dst_mac, conn) 
				print(f"\nInstalled flow rule on {name} to redirect packet on output port {port_out} when receiving it from MAC address {src_mac}\n")
				print(f"\nInstalled flow rule on {name} to redirect packet on output port {port_out_to_prev} when receiving it from MAC address {dst_mac} (reverse rule)\n")
		
				

		#Handle gateway: we need to install only the rule that enables to send packets from the gateway to previous node
		name = sp[len(sp)-1] #gw
		prev = sp[len(sp)-2]
		dpid_curr = None
		dpid_prev = None
		#Extract dpids correspondant to the node names
		for dpid in self.dpids:
			for i in self.switches[dpid]:
				if i.port_no == 65534:
					if i.name == name:
						dpid_curr = dpid
				if i.port_no == 65534:
					if i.name == prev:
						dpid_prev = dpid
		#get curr connection
		conn = None
		for k in self.connections:
			if k == dpid_curr:
				conn = self.connections[dpid_curr]
		
		dpid_curr_ = dpid_curr
		dpid_curr = dpidToStr(dpid_curr)
		dpid_prev = dpidToStr(dpid_prev)
		src_mac = None
		port_out_to_prev = None

		for i in self.links:
			#Scan prev <-> next link
			if (i.dpid1 == dpid_prev and i.dpid2 == dpid_curr):
				#Get output port of previous node, where the packet came from
				port_prev = i.port1
				port_out_to_prev = i.port2
				#Get MAC of source when it's not host
				for tup in self.switch_MACs[dpid_prev]:
					if tup[0] == port_prev:
						src_mac = tup[1]
						break

		self.install_flow_rule(dpid_curr_, port_out_to_prev, src_mac, conn)
		print(f"\nInstalled flow rule on gw to redirect packet on output port {port_out_to_prev} when receiving it from MAC address {src_mac}\n")
		
	
						 		
	def _handle_ConnectionUp(self, event):
		dpid = event.dpid
		self.connections[dpid] = event.connection			
		
	def _handle_PacketIn(self, event):
		packet = event.parsed
		src_addr = packet.src
		
		#If the packet is not coming from the host do not do anything
		if ( src_addr != EthAddr("00:00:00:00:00:23") and src_addr != EthAddr("00:00:00:00:00:24") and src_addr != EthAddr("00:00:00:00:00:33") and src_addr != EthAddr("00:00:00:00:00:34")):
			return
		if packet.find('ipv4') == None:
			return

		
		
		#GET GRAPH AND ALL THE RELEVANT STRUCTURES IF it's the first routing
		if len(self.marked_nodes) == 0:
			tup = core.linkDiscovery.getLinks()
			self.switches = tup[0] #switches
			for i in tup[1]:
				self.links.append(tup[1][i]) #save all links
			self.switch_MACs = tup[2] #dipd associated to a series of tuples (port, MAC of the port)
			print("DPID and MACS are: ", self.switch_MACs)
			
			#get dpid list from the discovery module
			for k in tup[3].keys():
				self.dpids.append(tup[3][k])
			
			#Create graph
			links_ = []
			for link in self.links:
				links_.append((link.name1,link.name2))
			
			self.graph = Graph()
			self.graph.add_edges_from(links_)
			
			#Get source node as the first switch the packet traverses
			#The algorithm should assign flow rules for everyone with the first AP traversal
			#We use names as h, s1, s2, r, etc... as identifiers of nodes
			src = ''
			for i in self.switches[event.dpid]:
				if i.port_no == 65534:
					src = i.name
					
			
		
			#Base case: no configured path exists, the internet is the goal, calculate shortest path to gateway
			sp = self.graph.shortest_path(source=src, target='gw')
		
			print("Shortest path is: ", sp)
				
			#Install flow rules on all path nodes
			self.sort_and_install(sp, event)
			
			for i in sp:
				#mark nodes as configured
				self.marked_nodes.append(i)
						 	
			
		
		#Else we apply algorithm to find less costly path in terms of rule appliance	
		#Cost modeling: the already configured path has cost 0 for every node, since it is already configured, every new node we have to configure on a path adds a cost of 1
		#Two paths are considered: the shortest path from the starting node to any node of the already configured path(from there the cost is 0), and the shortest path on the subgraph that does not contain the already configured path (getting an entirely new path may be less costly on some graphs than trying to reach the already configured path), unless the destination node is unreachable from the subgraph
		else:
			print("Recalculating path...")
			#Get source node as the first switch the packet traverses
			src = ''
			for i in self.switches[event.dpid]:
				if i.port_no == 65534:
					src = i.name
		
			
			
			#Compute subgraph with no nodes from the already configured path
			subgraph = Graph()
			if 'gw' in self.marked_nodes:
				self.marked_nodes.remove('gw')
			edges = []
			links_ = []
			for link in self.links:
				links_.append((link.name1, link.name2))
				
			
			for l in links_:
				if not ( l[0] or l[1] in marked_nodes ):
					edges.append((l[0], l[1]))
			
			subgraph.add_edges_from(edges)
			
			cost_path_1 = 0
			#If there is no gw node in the graph it means the graph got disconnected, pass onto second part and directly compute shortest path from the start node to the already configured path 
			if 'gw' in subgraph.nodes():
				#Calculate cost on subgraph
				for i in subgraph.nodes():
					if i != 'gw':
						cost_path_1 += 1
					
			else:
				cost_path_1 = 'inf' #destination node unreachable from subgraph
				
				
			#To calculate cost of the second path, we collapse all marked nodes into one node and add edges according
			cost_path_2 = 0
			
			subgraph2 = Graph()
			edges = []
			collapse = 'path'
			for l in links_:
				#All edges from one not-in-configured-path node to one node in the configured path or viceversa are inserted as the collapsed node and the node not in the path
				if l[0] in self.marked_nodes and l[1] not in self.marked_nodes:
					edges.append((collapse, l[1]))
				elif l[1] in self.marked_nodes and l[0] not in self.marked_nodes:
					edges.append((l[0], collapse))
				elif l[0] not in self.marked_nodes and l[1] not in self.marked_nodes:
					#We construct the rest of the graph as normal
					edges.append((l[0], l[1]))
					
			subgraph2.add_edges_from(edges)
			
			#We calculate shortest path from the starting node to the collapsed node (to any node of the already-configured-path)
			sp2 = subgraph2.shortest_path(source=src, target=collapse)
			for i in sp2:
				cost_path_2 += 1
				
			if cost_path_1 == 'inf':
				#The path is composed by all nodes inside 
				sp = self.marked_nodes
				for i in sp2:
					sp2.append(i)
				sort_and_install(sp, event)
			else:
				#In our topology this should never happen, to code later
				print("Other case")
							
			
			
			
			
		
	
def launch():
	core.registerNew(UserMobility)
		
		
	

