'''
This is one of the servers in the RAFT (?) distributed system.
Each member has a group view, a mode (normal node/manager node), and a log of what operations it has performed.
To be decided: communication protocol (TCP/UDP), membership management protocol (RAFT/Paxos/etc), other recovery mechanisms, service to be provided.
'''

import _thread, os, sys
import socket
import MemberLib as lib
import GroupView, Log
from State import State
import time
import struct
import random

SERVER_PORT = 45678  # Review
ERROR_CODE = 0  # Default

MULTICAST_ADDRESS = '224.3.29.71'     # 224.0.0.0 - 230.255.255.255 -> Addresses reserved for multicasting
MULTICAST_PORT = 45678

class Member:

    def __init__(self):
        self.group_view = GroupView
        self.log = Log

        # Determined at runtime
        self.id = None
        self.server_socket = None
        self.heartbeat_window_timer = None
        self.heartbeat_timeout_point = None
        self.heartbeat_received = False

        # End leader thread after sending a certain number of heartbeats, so that the followers will all timeout
        self.num_heartbeats_sent = 0


    def get_group_view(self):
        return self.group_view

    # Heartbeat timer loop - if you don't receive a heartbeat message within a certain length of time, become a candidate
    def heartbeat_timer_thread(self):

        self.heartbeat_timeout_point = time.time() + random.uniform(4, 10)  # Random delay - between 4 to 10 seconds

        while True:
            if self.state == State.follower:
                time.sleep(1);

                if self.heartbeat_received:
                    self.heartbeat_timeout_point = time.time() + random.uniform(4, 10)
                    self.heartbeat_received = False
                else:
                    current_time = time.time()
                    if current_time > self.heartbeat_timeout_point:
                        lib.print_message('Heartbeat timeout - I am now the leader', self.id)
                        self.state = State.leader

    # Loop - listen for multicast messages
    def multicast_listening_thread(self):
        while True:
            data, leader_address = self.server_socket.recvfrom(1024)
            lib.print_message('Received message from ' + str(leader_address) + ': ' + data.decode(), id)
            # self.server_socket.sendto('ack'.encode(), leader_address)  # Send acknowledgement

    # Startup node, configure socket
    def start_serving(self, id):
        self.id = id
        self.state = State.follower # All nodes begin in the follower state
        global ERROR_CODE

        lib.print_message('Online', id)

        try:

            _thread.start_new_thread(self.heartbeat_timer_thread, ())

            running = True

            while running:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # SOCK_STREAM = TCP, SOCK_DGRAM = UDP

                self.server_socket.settimeout(0.2)  # Set timeout so the socket does not block indefinitely while trying to receive data
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                follower_address = ('', MULTICAST_PORT)
                self.server_socket.bind(follower_address)

                # If you are the leader, regularly send heartbeat messages via multicast
                if self.state == State.leader:

                    # Set the time-to-live for messages to 1 so they do not go further than the local network segment
                    time_to_live = struct.pack('b', 1)
                    self.server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, time_to_live)

                    # Send heartbeat messages
                    while self.state == State.leader and running == True:
                        lib.print_message('Sending heartbeats', id)
                        heartbeat_message = 'heartbeat'
                        try:
                            leader_multicast_group = (MULTICAST_ADDRESS, MULTICAST_PORT)
                            self.server_socket.sendto(heartbeat_message.encode(), leader_multicast_group)
                            self.num_heartbeats_sent += 1

                        except Exception as e2:
                            lib.print_message('Exception e2: ' + str(e2), id)
                            ERROR_CODE = 1

                        # Shut down after sending a certain number of heartbeats, so that the followers will timeout
                        if self.num_heartbeats_sent >= 3:
                            #lib.print_message('Leader stepping down!', id)
                            #self.state = State.follower
                            #self.num_heartbeats_sent = 0
                            #self.heartbeat_timeout_point = time.time() + 10

                            lib.print_message('Leader shutting down!', id)
                            running = False

                        time.sleep(2);

                # If you are a follower, listen for heartbeat messages
                if self.state == State.follower:

                    # Add the socket to the multicast group
                    group = socket.inet_aton(MULTICAST_ADDRESS)
                    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
                    self.server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

                    # Loop - listen for heartbeats, as long as you are a follower
                    while self.state == State.follower and running == True:
                        try:
                            data, leader_address = self.server_socket.recvfrom(1024)

                            if data.decode() == 'heartbeat':
                                lib.print_message('Received heartbeat', id)
                                self.heartbeat_received = True

                            # self.server_socket.sendto('ack'.encode(), leader_address)  # Send acknowledgement
                        except Exception as e3:
                            if str(e3) == 'timed out':
                                pass    # Continue

        except Exception as e1:
            lib.print_message('Exception e1: ' + str(e1), id)
            ERROR_CODE = 1
        finally:
            sys.exit(ERROR_CODE)

member = Member()
_thread.start_new_thread(member.start_serving, (random.randint(0, 100),))

while 1:
  sys.stdout.flush()    # Print output to console instantaneously