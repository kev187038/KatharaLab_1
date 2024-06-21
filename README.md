# How to run the applications
```bash
python3.9 ./pox.py <application_1> ... <application_n>
```
```bash
./pox/pox.py discovery_channel user_mobility fake_gateway host_tracking
```
Remember pox will be in ./pox, after loading the controller wait a bit for the links to be discovered! After they are discovered (the controller will send some messages), you can start pinging the internet module from the host using the interfaces with
```bash
 ping -I eth0/1/2/3 -c <num_packets> 100.0.0.1
```
and you should see the user_mobility and host_tracking modules in action, while fake_gateway will provide the necessary layer 2 support underneath.

# Second project
The second laboratory project is available at my colleague's repository at https://github.com/CogSP/distributed_consensus_p4
