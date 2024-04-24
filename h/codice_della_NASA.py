import time
import socket
import os
import random

ip_destinazione = "100.0.0.1"  
porta_destinazione = 12345  
messaggio = "Hello, this is a test message"


def invia_messaggio(ip_destinazione, porta_destinazione, messaggio):
    while True:
        interfaces = ["eth0", "eth1", "eth2", "eth3"]
        random_interface = interfaces[random.randrange(4)]
        os.system(f"ping -I {random_interface} -w 10 100.0.0.1")
        time.sleep(10)


def main():
    invia_messaggio(ip_destinazione, porta_destinazione, messaggio) 

if __name__ == "__main__":
    main()
