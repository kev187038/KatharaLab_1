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
    def __init__ (self, interface):
        Event.__init__(self)
        self.interface = interface

class HostTracking (EventMixin):

    _eventMixin_events = set( [ HostTracked ])

    def __init__(self):
        self.s4 = ""
        self.s3 = ""
        core.openflow.addListeners(self)

    def _handle_ConnectionUp(self, event):
        print("[in Host Tracking:] we are in _handle_ConnectionUp")
        for port in event.ofp.ports:
            if port.name == "s4":
                print("prova s4")
                self.s4 = dpidToStr(event.dpid)
            elif port.name == "s3":
                print("prova s3")
                self.s3 = dpidToStr(event.dpid)

    def _handle_PacketIn(self, event):
        print("[in Host Tracking:] we are in _handle_PacketIn")
        print("event.dpid: " + dpidToStr(event.dpid))
        print("s3 dpid: " + self.s3)
        print("s4 dpid: " + self.s4)
        
        if dpidToStr(event.dpid) != self.s4 and dpidToStr(event.dpid) != self.s3:
            return
        
        event_dpid = dpidToStr(event.dpid)

        if  event_dpid == self.s3:
            print("hey the host is connected to s3!")
            packet = event.parsed

            print("precisely, the packet source address is: " + str(packet.src))
            #if packet.find('ipv4') != None:

            # this is eth0
            if packet.src == "00:00:00:00:00:23":
                print("\t precisely, eth0")

            # this is eth2
            if packet.src == "00:00:00:00:00:33":
                print("\t precisely, eth2")
            
            self.raiseEvent(HostTracked(packet))

#            else:
 #               print("bo poi vediamo nel caso in cui il pacchetto non contenga l'indirizzo ip")

        if dpidToStr(event.dpid) == self.s4:
            print("hey the host is connected to s3!")
  #          if packet.find('ipv4') != None:
            packet = event.parsed
            
            print("precisely, the packet source address is: " + str(packet.src))
            

            # this is eth1
            if packet.src == "00:00:00:00:00:24":
                print("\t precisely, eth1")

            # this is eth3
            if packet.src == "00:00:00:00:00:34":
                print("\t precisely, eth3")
            
            self.raiseEvent(HostTracked(packet))

#            else:
 #               print("bo poi vediamo nel caso in cui il pacchetto non contenga l'indirizzo ip")


def launch():
    ht = HostTracking()
    core.register("host_tracking", ht)