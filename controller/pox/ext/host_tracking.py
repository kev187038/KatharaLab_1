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

class HostTracked (Event):
    def __init__ (self, packet):
        Event.__init__(self)
        self.packet = packet

class HostTracking (EventMixin):

    _eventMixin_events = set([HostTracked])

    def __init__(self):
        self.position_tracking = None
        core.openflow.addListeners(self)

    
    def _handle_PacketIn(self, event):
        packet = event.parsed
        linksList = core.linkDiscovery.links
        addresses = ["00:11:22:33:44:55"]

        for l in linksList:
            sid = linksList[l].sid1
            interface = linksList[l].port1
            addresses.append("00:00:00:00:00:" + str(sid) +""+ str(interface))


        #print(f"addresses {addresses}")

        if packet.src not in addresses:
            #print(f"packet.src = {packet.src}")
            self.position = (packet.src.toStr(), packet.src.toStr().split(':')[5][1], packet.src.toStr().split(':')[5][0])
            print(f"Mobile host is connected to S{packet.src.toStr().split(':')[5][0]}, on the interface {packet.src.toStr().split(':')[5][1]} ")
            self.raiseEvent(HostTracked(packet))
          
        return        
            

def launch():
    ht = HostTracking()
    core.register("host_tracking", ht)
