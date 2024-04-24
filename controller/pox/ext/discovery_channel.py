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
#import numpy as np


class Link():

	def __init__(self, sid1, sid2, dpid1, port1, dpid2, port2):
		self.name = str(sid1) + "_" + str(sid2)
		self.sid1 = sid1
		self.sid2 = sid2
		self.dpid1 = dpidToStr(dpid1)
		self.dpid2 = dpidToStr(dpid2)
		self.port1 = int(port1)
		self.port2 = int(port2)

class linkDiscovery():

	def __init__(self):
		self.switches = {}
		self.links = {}
		self.switch_id = {}
		self.id = 1
		core.openflow.addListeners(self)
		Timer(15, self.sendProbes, recurring=True)

	def _handle_ConnectionUp(self, event):
		self.switch_id[self.id] = event.dpid
		self.switches[event.dpid] = event.ofp.ports
		self.install_flow_rule(event.dpid)
		print("[In discovery_channel:] Connection Up: " + dpidToStr(event.dpid) + ", " + str(self.id))
		self.id += 1

	def _handle_PacketIn(self, event):
		#print("[In discovery_channel:] Packet In Detected... ", end='')
		eth_frame = event.parsed
		if eth_frame.src == EthAddr("00:11:22:33:44:55"):
			#print("[In discovery_channel:] it's a probe (Eth Addr Src is 00:11:22:33:44:55)")
			eth_dst = eth_frame.dst.toStr().split(':')
			sid1 = int(eth_dst[5][0])
			dpid1 = self.switch_id[sid1]
			port1 = int(eth_dst[5][1])
			dpid2 = event.dpid
			sid2 = ""
			for port in self.switches[dpid2]:
				if port.port_no == 65534:
					sid2 = str(port.name[-1])
			port2 = event.ofp.in_port
			link = Link(sid1, sid2, dpid1, port1, dpid2, port2)
			if link.name not in self.links:
				self.links[link.name] = link
				print("[In discovery_channel:] discovered new link: " + link.name)
				print(link.__dict__)

	def sendProbes(self):
		for sid in self.switch_id:
			dpid = self.switch_id[sid]
			name = ""
			for port in self.switches[dpid]:
				if port.port_no == 65534:
					name = str(port.name[-1])

			for port in self.switches[dpid]:
				# the 65534 port connects the dataplane with the control plane
				if port.port_no != 65534:
					mac_src = EthAddr("00:11:22:33:44:55")
					mac_dst = EthAddr("00:00:00:00:00:" + name + "" + str(port.name[-1]))
					ether = ethernet()
					ether.type = ethernet.ARP_TYPE
					ether.src = mac_src
					ether.dst = mac_dst
					ether.payload = arp()
					msg = of.ofp_packet_out()
					msg.data = ether.pack()
					msg.actions.append(of.ofp_action_output(port = port.port_no))
					core.openflow.sendToDPID(dpid, msg)

	# def getGraph(self, previousPath):
	# 	N = len(self.switches)
	# 	adj = np.zeros((N, N))

	# 	if previousPath is not None:
	# 		for link in self.links:
	# 			if link in previousPath:
	# 				adj[self.links[link].sid1, self.links[link].sid2] = 1
	# 			elif any(node in link for node in previousPath):
	# 				adj[self.links[link].sid1, self.links[link].sid2] = 2
	# 			else:
	# 				adj[self.links[link].sid1, self.links[link].sid2] = 3

	# 	else:
	# 		for link in self.links:
	# 			adj[self.links[link].sid1, self.links[link].sid2] = 1

	# 	graph = nx.from_numpy_matrix(np.where(adj > 0, 1, 0))
	# 	return graph


	def install_flow_rule(self, dpid):
		msg = of.ofp_flow_mod()
		msg.priority = 50000
		match = of.ofp_match(dl_src = EthAddr("00:11:22:33:44:55"))
		msg.match = match
		msg.actions = [of.ofp_action_output(port = of.OFPP_CONTROLLER)]
		core.openflow.sendToDPID(dpid, msg)


def launch():
	core.registerNew(linkDiscovery)