import pox
from pox.lib.revent import *

from pox.core import core                     # Main POX object
import pox.openflow.libopenflow_01 as of      # OpenFlow 1.0 library
import pox.lib.packet as pkt                  # Packet parsing/construction
from pox.lib.addresses import EthAddr, IPAddr # Address types
import pox.lib.util as poxutil                # Various util functions
import pox.lib.revent as revent               # Event library
import pox.lib.recoco as recoco               # Multitasking library
from pox.lib.revent.revent import Event
from pox.lib.revent.revent import EventMixin
from pox.lib.util import dpid_to_str
from pox.lib.packet import arp

class FakeGateway(EventMixin):

  def __init__(self):
    self.GW_MAC = ""
    core.openflow.addListeners(self)

  def _handle_ConnectionUp (self, event):
    print("[in reflector:] in _handle_ConnectionUp")

    for port in event.ofp.ports:
      gw_ports = [port for port in event.ofp.ports if port.name == "gw"]
        if len(gw_ports) > 0:
            non_gw_ports = [port for port in event.ofp.ports if port.name != "gw"]
            self.gwMACaddr = non_gw_ports[0].hw_addr

  def _handle_PacketIn (self, event):
    print("[in reflector:] in _handle_PacketIn")

    packet = event.parsed
    arp_packet = packet.find('arp')

    if arp_packet.opcode != arp.REQUEST:
      return
    
    # Handle ARP request 
    print("this is an ARP request")
    arp_reply = arp() 
    arp_reply.hwsrc = self.GW_MAC 
    arp_reply.hwdst = arp_packet.hwsrc 
    arp_reply.opcode = arp.REPLY 
    #arp_reply.protosrc = arp_packet.protodst 
    #arp_reply.protodst = arp_packet.protosrc 
    ether = pkt.ethernet() 
    ether.type = pkt.ethernet.ARP_TYPE 
    ether.dst = arp_packet.hwsrc 
    ether.src = self.GW_MAC
    ether.payload = arp_reply 
    msg = of.ofp_packet_out() 
    msg.data = ether.pack() 
    msg.actions.append(of.ofp_action_output(port = event.port)) 
    msg.in_port = event.port 
    event.connection.send(msg)
    print("packet sent!")



def launch ():
  print("[in reflector:] launch function activated... ")
  reflector = Reflector()
  core.register("reflector", reflector)

