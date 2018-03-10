'''
    This is one of the server nodes in the RAFT distributed system. The service provided to the client will be to give them the current membership of the group.
    Each member has a group view, a mode (follower/candidate/leader), and a log of what operations it has performed.
    UDP is used for communication. Heartbeats are used to maintain the group view of every node, and message sequencing is used to detect message loss.
    Other recovery mechanisms, client service to be provided.
'''

import _thread, sys
import socket
import MemberLib as lib
import MessageType
import GroupView as GroupView
from State import State
import time
import struct
import random
import logging
import pickle
import Message as Message
sys.path.append("../")

logging.basicConfig(
    filename="DistributedManagementSystem.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s"
)

'''  Server constants '''
SERVER_PORT = 45678  # Review
DEFAULT_STATE = State.follower

MULTICAST_ADDRESS = '224.3.29.71'     # 224.0.0.0 - 230.255.255.255 -> Addresses reserved for multicasting
MULTICAST_PORT = 45678

''' Generic constants '''
RECV_BYTES = 1024
SLEEP_TIMEOUT = 1


class Member:

    def __init__(self, state, _id):
        self.id = _id
        self.server_socket = None
        self.heartbeat_timeout_point = None
        self.heartbeat_received = False
        self.group_view = GroupView.GroupView()
        self.running = None

        # End leader thread after sending a certain number of heartbeats, so that the followers will all timeout
        self.num_heartbeats_sent = 0
        # Current term for voting, needed to ensure that members can only vote once per term
        # Int is unbounded in Python 3 so I think using this as an infinite counter is no problem
        self.term = 0
        self.voted = False

        # Set state to default 'follower' if not specified
        if State.has_value(state) and state is not 'candidate':
            self.state = State[state]
        else:
            self.state = DEFAULT_STATE

    def get_group_view(self):
        return self.group_view

    # Heartbeat timer loop - if you don't receive a heartbeat message within a certain length of time, become a candidate
    def heartbeat_timer_thread(self):
        # Random delay - between 4 to 10 seconds
        # TODO add this to documentation (Will help with report later)
        self.heartbeat_timeout_point = lib.get_random_timeout()

        while self.running is True:
            if self.state == State.follower:
                time.sleep(SLEEP_TIMEOUT)

                if self.heartbeat_received:
                    # Reset timeout interval
                    self.heartbeat_timeout_point = lib.get_random_timeout()
                    self.heartbeat_received = False
                else:
                    if time.time() > self.heartbeat_timeout_point:
                        lib.print_message('Heartbeat timeout - I am now a candidate', self.id)
                        self.state = State.candidate
            elif self.state == State.leader:
                try:
                    message, follower_address = self.server_socket.recvfrom(RECV_BYTES)
                    message = pickle.loads(message)
                    if message.get_message_type() == MessageType.MessageType.heartbeat_ack and message.get_term() == self.term:
                        lib.print_message('Heartbeat acknowledgement received from ' + follower_address, self.id)
                except Exception as e:
                    if str(e) == 'timed out':
                        pass  # Continue
                    pass

    # Loop - listen for multicast messages
    def multicast_listening_thread(self):
        while True:
            message, leader_address = self.server_socket.recvfrom(RECV_BYTES)
            message = pickle.loads(message)
            lib.print_message('Received message from ' + str(leader_address) + ': ' + message.get_data(), id)
            # self.server_socket.sendto('ack'.encode(), leader_address)  # Send acknowledgement

    # Startup node, configure socket
    def start_serving(self):
        lib.print_message('Online in state {0}'.format(self.state), self.id)

        try:
            _thread.start_new_thread(self.heartbeat_timer_thread, ())
            self.running = True

            while self.running:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # SOCK_STREAM = TCP, SOCK_DGRAM = UDP
                # Set timeout so the socket does not block indefinitely while trying to receive data
                self.server_socket.settimeout(0.2)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                follower_address = ('', MULTICAST_PORT)
                self.server_socket.bind(follower_address)

                # If you are the leader, regularly send heartbeat messages via multicast
                if self.state == State.leader:
                    # Set the time-to-live for messages to 1 so they do not go further than the local network segment
                    time_to_live = struct.pack('b', 1)
                    self.server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, time_to_live)

                    # Send heartbeat messages
                    while self.state == State.leader and self.running is True:
                        lib.print_message('Sending heartbeats', self.id)
                        heartbeat_message = 'heartbeat'
                        try:
                            leader_multicast_group = (MULTICAST_ADDRESS, MULTICAST_PORT)
                            self.server_socket.sendto(heartbeat_message.encode(), leader_multicast_group)
                            self.num_heartbeats_sent += 1

                        except Exception as e2:
                            lib.print_message('Exception e2: ' + str(e2), self.id)

                        # Shut down after sending a certain number of heartbeats, so that the followers will timeout
                        # TODO document - this is part of our test framework
                        #if self.num_heartbeats_sent >= 3:
                        #lib.print_message('Leader stepping down!', id)
                        #self.state = State.follower
                        #self.num_heartbeats_sent = 0
                        #self.heartbeat_timeout_point = time.time() + 10

                        #lib.print_message('Leader shutting down!', id)
                        #self.running = False

                        time.sleep(SLEEP_TIMEOUT * 2)

                # If you are a follower, listen for heartbeat messages
                if self.state == State.follower:

                    # Add the socket to the multicast group
                    group = socket.inet_aton(MULTICAST_ADDRESS)
                    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
                    self.server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

                    while self.state == State.follower and self.running is True:
                        self.do_follower_message_listening()

                if self.state == State.candidate:
                    # Request votes through broadcast message
                    votes_needed = (self.group_view.get_size() / 2) + 1
                    # Start by voting for itself
                    votes_received = 1
                    voters = []
                    multicast_group = (MULTICAST_ADDRESS, MULTICAST_PORT)
                    self.term += 1
                    self.server_socket.sendto(pickle.dumps(Message.Message(self.term, MessageType.MessageType.vote_request, '')), multicast_group)

                    # Loop - wait for votes
                    # Todo Should Groupview be edited?
                    while self.state == State.candidate and self.running is True:
                        try:
                            message, address = self.server_socket.recvfrom(RECV_BYTES)
                            message = pickle.loads(message)

                            if votes_received >= votes_needed:
                                lib.print_message('Sufficient votes received - I am now a leader', self.id)
                                self.state = State.leader
                            elif message.get_message_type() == MessageType.MessageType.vote and message.get_term() == self.term:
                                lib.print_message('Vote received from ' + address, self.id)
                                if not voters.__contains__(address):
                                    voters.append(address)
                                    votes_received += 1
                                if votes_received >= votes_needed:
                                    lib.print_message('Sufficient votes received - I am now a leader', self.id)
                                    self.state = State.leader
                            elif message.get_term > self.term:
                                lib.print_message('My term is outdated - I am now a follower', self.id)
                                self.state = State.follower
                            elif message.get_message_type() == MessageType.MessageType.heartbeat:
                                lib.print_message('Other leader found - I am now a follower', self.id)
                                self.state = State.follower
                                self.term = message.get_term()
                        except Exception as e4:
                            if str(e4) == 'timed out':
                                lib.print_message("Candidate timeout", self.id)
                                pass    # Continue
        except Exception as e1:
            lib.print_message('Exception e1: ' + str(e1), self.id)
        finally:
            sys.exit(1)

    # Loop - listen for heartbeats, as long as you are a follower
    def do_follower_message_listening(self):
        try:
            message, sender = self.server_socket.recvfrom(RECV_BYTES)
            message = pickle.loads(message)

            if message.get_term() > self.term:
                self.term = message.get_term()
                self.voted = False

            if message.get_message_type() == MessageType.MessageType.heartbeat:
                lib.print_message('Received heartbeat', self.id)
                self.heartbeat_received = True
                self.server_socket.sendto(
                    pickle.dumps(Message.Message(self.term, MessageType.MessageType.heartbeat_ack, '')), sender)

            elif message.get_message_type() == MessageType.MessageType.vote_request:
                if message.get_term() == self.term or (message.get_term() == self.term and self.voted is False):
                    self.server_socket.sendto(
                        pickle.dumps(Message.Message(self.term, MessageType.MessageType.heartbeat_ack, '')), sender)
                    self.voted = True
                    # self.server_socket.sendto('ack'.encode(), leader_address)  # Send acknowledgement
        except Exception as e3:
            if str(e3) == 'timed out':
                pass  # Continue

    def respond_to_client_request(self, client_message):
        # TODO implement this
        pass


if __name__ == "__main__":
    starting_state = sys.argv[1]
    member = Member(starting_state, random.randint(0, 100))
    _thread.start_new_thread(member.start_serving, ())

    while 1:
        sys.stdout.flush()    # Print output to console instantaneously
