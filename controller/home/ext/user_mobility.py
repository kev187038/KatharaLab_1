import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.recoco import Timer
from pox.lib.revent.revent import EventMixin
from pox.lib.revent.revent import Event
from pox.lib.addresses import EthAddr
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.arp import arp
from pox.lib.packet.lldp import lldp
from pox.lib.util import dpidToStr
import time

import networkx as nx

# TODO: PUT A VERBOSE VARIABLE THAT IF IT'S SET SHOW ALL THE PRINT ON THE COMMAND LINE
# MAYBE IT CAN BE USEFUL FOR THE ORAL EXAMINATION

class UserMobility():

	def __init__(self):
		self.links = {} # afterwards it will be core.linkDiscovery.links
		self.first_time = True
		self.old_path = []
		core.host_tracking.addListeners(self)
		core.openflow.addListeners(self)

	# the first time a packet in occurs we create the path with Dijkstra
	# after this time the path will be computed with the minimum configuration
	def _handle_PacketIn(self, event):

		eth_frame = event.parsed
		
		if eth_frame.type == eth_frame.ARP_TYPE:
			return
		
		print("[in UserMobility:] handling Packet In, creating the path from scratch with Dijkstra")
		
		ip_pkt = eth_frame.payload
		ip_src = ip_pkt.srcip
		ip_dst = ip_pkt.dstip
		switch_src = self.host_location[ip_src.toStr()]
		switch_dst = self.host_location[ip_dst.toStr()]
		S = list(core.linkDiscovery.switch_id.keys())[list(core.linkDiscovery.switch_id.values()).index(switch_src)]
		D = list(core.linkDiscovery.switch_id.keys())[list(core.linkDiscovery.switch_id.values()).index(switch_dst)]
		graph = core.linkDiscovery.getGraph()
		path = nx.shortest_path(graph, S, D)
		self.first_time = False


								  # event is event.parsed of handle_PacketIn
	def _handle_HostTracked(self, event):

		eth_frame = event
		host_interface = eth_frame.src
		print("[in UserMobility:] handling Host Tracked event, we discover that the host is connected to", end='')
		print(host_interface)
		self.links = core.linkDiscovery.links
		print("the list of links is now", end='')
		print(self.links)

		if self.first_time != False:
			print("there is a problem, first_time should be false")
			return

		if eth_frame.type == eth_frame.ARP_TYPE:
			return
		
		ip_pkt = eth_frame.payload
		ip_src = ip_pkt.srcip
		ip_dst = ip_pkt.dstip
		switch_src = self.host_location[ip_src.toStr()]
		switch_dst = self.host_location[ip_dst.toStr()]
		S = list(core.linkDiscovery.switch_id.keys())[list(core.linkDiscovery.switch_id.values()).index(switch_src)]
		D = list(core.linkDiscovery.switch_id.keys())[list(core.linkDiscovery.switch_id.values()).index(switch_dst)]
		graph = core.linkDiscovery.getGraph(self.old_path)
		path = nx.shortest_path(graph, S, D)
		
		
def launch():
	user_mobility = UserMobility()
	core.register("user_mobility", user_mobility)
