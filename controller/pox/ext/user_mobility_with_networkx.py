import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.arp import arp
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.util import dpidToStr
import networkx as nx

class User_mobility():

	def __init__(self):
		core.openflow.addListeners(self)
		core.HostTracking.addListeners(self)
		self.host_location = {}
		self.host_ip_mac = {}
		self.previousPath = None

	#def _handle_ConnectionUp(self, event):
	#    core.Host_tracking._handle_PacketIn(event)
	
	def dijkstra(self, graph, source, destination):
	    best_path = nx.shortest_path(graph, source=source, target=destination)
	    return best_path
    
	def _handle_UserIsMoving(self, event):
		eth_frame = event.packet
		if eth_frame.type == ethernet.IP_TYPE:
			ip_pkt = eth_frame.payload
			ip_src = ip_pkt.srcip
			ip_dst = ip_pkt.dstip
			switch_src = self.host_location[ip_src.toStr()]
			switch_dst = self.host_location[ip_dst.toStr()]
			S = list(core.linkDiscovery.switch_id.keys())[list(core.linkDiscovery.switch_id.values()).index(switch_src)]
			D = list(core.linkDiscovery.switch_id.keys())[list(core.linkDiscovery.switch_id.values()).index(switch_dst)]
			
			graph = core.topology_Discovery.getGraph(self.previousPath)		
			path = self.dijkstra(graph, source=S, destination=D)
			self.previousPath = path
			self.install_flow_rules(path)
			print(path)
			
	def install_flow_rules(self, path):
	    for i in range(len(path)-1):
	        src_switch = path[i]
	        dst_switch = path[i+1]
	        link = core.linkDiscovery.links[str(src_switch) + "_" + str(dst_switch)]
	        
	        msg = of.ofp_flow_mod()
	        msg.priority = 1000
	        msg.match = of.ofp_match()
	        msg.match.dl_dst = EthAddr(self.host_ip_mac[ip_dst.toStr()])
	        msg.match.dl_src = EthAddr(self.host_ip_mac[ip_src.toStr()])
	        msg.actions.append(of.ofp_action_output(port=link.port1))
	        core.openflow.sendToDPID(link.dpid1, msg)
	        
	        msg = of.ofp_flow_mod()
	        msg.priority = 1000
	        msg.match = of.ofp_match()
	        msg.match.dl_dst = EthAddr(self.host_ip_mac[ip_src.toStr()])
	        msg.match.dl_src = EthAddr(self.host_ip_mac[ip_dst.toStr()])
	        msg.actions.append(of.ofp_action_output(port=link.port2))
	        core.openflow.sendToDPID(link.dpid2, msg)

def launch():
	core.registerNew(User_mobility)
