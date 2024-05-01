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
		#print("Edges are: ",self.edges)
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
		#print("Predecessors are: ",predecessors)
		
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
		self.gw_dpid = None 
		
	def install_flow_rule(self, out_port, dl_addr, conn):
		msg = of.ofp_flow_mod()
		msg.priority = 50000
		match = of.ofp_match(dl_src = dl_addr, dl_type = ethernet.IP_TYPE) #must be IP and with correct source MAC of the path
		msg.match = match
		action = of.ofp_action_output(port=out_port) #redirect packet on out_port
		msg.actions.append(action)
		conn.send(msg)
			
	def sort_and_install(self, sp, event):
		for i in range(len(sp)-1):

			#Use self.events to extract the link, we analyze prev<->curr<->next nodes
			prev = None
			if (i - 1 >= 0):
				prev = sp[i-1]
			curr = sp[i]
			next = sp[i+1]
			
			curr_next = None
			#Get link representing curr<->next
			for link in self.links:
				if link.name1 == curr and link.name2 == next:
					curr_next = link
					break
			
			prev_curr = None
			#Get link representing prev<->next
			for link in self.links:
				if link.name1 == prev and link.name2 == curr:
					prev_curr = link
					break
			
			if curr_next == None:
				print("Error links not found")
				exit(1) #should not happen

			#We get the <-curr-> ports directions and MACs to match for the rules, especially MAC of host
			h_mac = event.parsed.src
			if prev_curr == None:
				#This means we have the host as prev
				port_out_to_prev = event.port
				print(f"Dealing with host with mac {h_mac} and port to it {port_out_to_prev}")
			else:
				port_out_to_prev = prev_curr.port2

			port_out = curr_next.port1
			dst_mac = curr_next.mac2
			
			#get curr connection (flow rules will be installed on current inspected node)
			conn = None
			dpid_curr = curr_next.raw_dpid1
			for k in self.connections.keys():
				if k == dpid_curr:
					conn = self.connections[dpid_curr]	
		
			#Should never happen				
			if port_out == None or port_out_to_prev == None or conn == None:
				print("Error information not found!")
				exit(1)
			
			dst_mac = EthAddr("00:00:00:00:00:11")
				
			#Install flow rules for curr -> next and next -> curr packet exchange		 
			self.install_flow_rule(port_out, h_mac, conn) 
			self.install_flow_rule(port_out_to_prev, dst_mac, conn) 
			print(f"Installed flow rule on {curr} to redirect packet on output port {port_out} when receiving it from MAC address {h_mac}")
			print(f"Installed flow rule on {curr} to redirect packet on output port {port_out_to_prev} when receiving it from MAC address {dst_mac}\n")

		#Handle gateway separately
		gw = sp[-1]
		l = None
		for link in self.links:
			if link.name2 == gw: #link (s2, gw) (s5)
				l = link
				break
		conn = None
		port = l.port2
		dpid_gw = l.raw_dpid2
		for k in self.connections.keys():
			if k == dpid_gw:
				conn = self.connections[dpid_gw]
			
		#Install flow rule gw->internet
		msg = of.ofp_flow_mod()
		msg.priority = 50000
		match = of.ofp_match(in_port=port) 
		msg.match = match
		change_mac = of.ofp_action_dl_addr.set_dst(EthAddr("00:00:00:00:00:11")) #Change mac to Internet mac so that internet node will accept the packet
		#postilla, bisogna aggiornare per impedire al gw di fare redirect delle arp request del nodo int
		action = of.ofp_action_output(port=2) #redirect packet on out_port
		msg.actions.append(change_mac)
		msg.actions.append(action)
		conn.send(msg)
		
		#Install flow rule Internet->gw->s2
		msg2 = of.ofp_flow_mod()
		msg2.priority = 50000
		match2 = of.ofp_match(in_port=2) 
		msg2.match = match2
		change_mac2 = of.ofp_action_dl_addr.set_dst(event.parsed.src)  #Change mac to host mac for same reasons
		action2 = of.ofp_action_output(port=port)
		msg2.actions.append(change_mac2)
		msg2.actions.append(action2)
		conn.send(msg2)
			 		
	def _handle_ConnectionUp(self, event):
		dpid = event.dpid
		self.connections[dpid] = event.connection
		
	def _handle_PacketIn(self, event):
		packet = event.parsed
		src_addr = packet.src
		
		#If the packet is not coming from the host do not do anything
		if (src_addr != EthAddr("00:00:00:00:00:23") and src_addr != EthAddr("00:00:00:00:00:24") and src_addr != EthAddr("00:00:00:00:00:33") and src_addr != EthAddr("00:00:00:00:00:34")):
			#print("[user_mobility packetIn handler:] the packet does not come from the host", flush=True)
			return
		if packet.find('ipv4') == None:
			#print("[user_mobility packetIn handler:] the packet does not contain ipv4", flush=True)
			return

		print("Event raised by, ",dpidToStr(event.connection.dpid))
		
		#FIRST TIME ROUTING INITIALIZATION
		#GET GRAPH AND ALL THE RELEVANT STRUCTURES IF it's the first routing
		if len(self.marked_nodes) == 0:
			tup = core.linkDiscovery.getLinks()
			self.switches = tup[0] #switches
			for i in tup[1]:
				self.links.append(tup[1][i]) #save all links
			self.switch_MACs = tup[2] #dipd associated to a series of tuples (port, MAC of the port)
			
			#get dpid list from the discovery module
			for k in tup[3].keys():
				self.dpids.append(tup[3][k])
			
			#Create graph
			links_ = []
			for link in self.links:
				links_.append(("s"+str(link.sid1),"s"+str(link.sid2)))
			self.graph = Graph()
			self.graph.add_edges_from(links_)
			
			#Get gw dpid
			for i in self.links:
				if i.name1 == 's5':
					self.gw_dpid = i.raw_dpid1
					break
			
			#Get source node as the first switch the packet traverses
			#The algorithm should assign flow rules for everyone with the first AP traversal
			#We use names as h, s1, s2, r, etc... as identifiers of nodes
			src = ''
			for i in self.switches[event.dpid]:
				if i.port_no == 65534:
					src = i.name
		
			#Base case: no configured path exists, the internet is the goal, calculate shortest path to gateway
			sp = self.graph.shortest_path(source=src, target='s5')

			print("Shortest path is: ", sp)
				
			#Install flow rules on all path nodes
			self.sort_and_install(sp, event)
			
			#Install on gw (done 1 time)
			self.install_gateway_rules(sp, event)
			
			for i in sp:
				#mark nodes as configured
				if i != "s5":
					self.marked_nodes.append(i)
				
		#Else we apply algorithm to find less costly path in terms of rule reconfiguration	
		#Cost modeling: the already configured path has cost 0 for every node, since it is already configured, every new node we have to configure on a path adds a cost of 1
		#Two paths are considered: the shortest path from the starting node to any node of the already configured path(from there the cost is 0), and the shortest path on the subgraph that does not contain the already configured path (getting an entirely new path may be less costly on some graphs than trying to reach the already configured path), unless the destination node is unreachable from the subgraph
		else:
			print("Recalculating path...")
			#Get source node as the first switch the packet traverses
			src = ''
			for i in self.switches[event.dpid]:
				if i.port_no == 65534:
					src = i.name
			
			print("Old path was ", self.marked_nodes)
			#Get old path nodes and coalesce them into a unique node, (the gw is the goal and won't be considered in the old path)
			all_edges = self.graph.edges
			edge_dict = {} #memorize key nodes and edges of nodes as values
			for e in all_edges:
				edge_dict[e[0]] = []
			for e in all_edges:
				edge_dict[e[0]].append(e[1])
	
def launch():
	core.registerNew(UserMobility)
