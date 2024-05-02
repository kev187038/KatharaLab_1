import pox
from pox.lib.revent import *
from pox.core import core 
import pox.openflow.libopenflow_01 as of 
import pox.lib.packet as pkt    
from pox.lib.addresses import EthAddr, IPAddr 
import pox.lib.util as poxutil               
import pox.lib.revent as revent               
import pox.lib.recoco as recoco              
from pox.lib.revent.revent import Event
from pox.lib.revent.revent import EventMixin
from pox.lib.util import dpidToStr
from pox.lib.packet import arp

class Fake_GateWay(EventMixin):

  def __init__(self):
    self.GW_MAC = "" #Gateway MAC
    core.openflow.addListeners(self)
    self.gw_connection = None

  def _handle_ConnectionUp (self, event):
    
    #Extract from discovery module the dpid and connection of gateway
    for port in event.ofp.ports:
      if port.name == "s5":
        self.gw_connection = event.connection
        # if the list contains gw there is the other interface
        # that is the one we are interested in

        # there are only 2 elements in this list
        #print("number of elements in ports:" + str(len(event.ofp.ports)))
        for port in event.ofp.ports:
          if port.name != "s5":
            self.GW_MAC = port.hw_addr
  

  def _handle_PacketIn (self, event):

    packet = event.parsed
    arp_packet = packet.find('arp')
    
    if not arp_packet:
    	return

    #This is for arp only
    if arp_packet.opcode != arp.REQUEST:
      return
      
  
    
    #Handle ARP request by responding with arp reply
    arp_reply = arp() 
    arp_reply.hwsrc = self.GW_MAC 
    arp_reply.hwdst = packet.src
    arp_reply.protosrc = arp_packet.protodst 
    arp_reply.protodst = arp_packet.protosrc 
    arp_reply.opcode = arp.REPLY 
     
    ether = pkt.ethernet() 
    ether.type = pkt.ethernet.ARP_TYPE 
    ether.dst = packet.src 
    ether.src = self.GW_MAC
    ether.payload = arp_reply 
    
    msg = of.ofp_packet_out() 
    msg.data = ether.pack() 
    msg.actions.append(of.ofp_action_output(port = event.port))
    event.connection.send(msg)
    
    print("Answered ARP request.")

def launch ():
  fake_gateway = Fake_GateWay()
  core.register("Fake_GateWay", fake_gateway)

