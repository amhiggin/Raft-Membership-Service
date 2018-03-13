'''
    This is one of the server nodes in the RAFT distributed system. The service provided to the client will be to give them the current membership of the group.
    Each member has a group view, a mode (follower/candidate/leader), and a log of what operations it has performed.
    UDP is used for communication. Heartbeats are used to maintain the group view of every node, and message sequencing is used to detect message loss.
    Other recovery mechanisms, client service to be provided.
'''

import _thread, sys
import socket
import MemberLib as lib
from DistributedManagementSystem import MessageType
import GroupView as GroupView
from State import State
import time
import struct
import logging
import pickle
from DistributedManagementSystem import Message as Message
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

    def __init__(self, state, starting_number_of_nodes_in_group, _id):
        self.id = _id
        self.server_socket = None
        self.multicast_listener_socket = None
        self.heartbeat_timeout_point = None
        self.election_timeout_point = None
        self.heartbeat_received = False
        self.ready_to_run_for_election = False
        self.group_view = GroupView.GroupView(starting_number_of_nodes_in_group)
        self.running = None
        self.num_heartbeats_sent = 0
        self.term = 0
        self.voted = False
        if State.has_value(state) and state is not 'candidate':
            self.state = State[state]
        else:
            self.state = DEFAULT_STATE

    # Heartbeat timer loop - if you don't receive a heartbeat message within a certain length of time, become a candidate
    def heartbeat_and_election_timer_thread(self):

        self.heartbeat_timeout_point = lib.get_random_timeout()
        self.election_timeout_point = lib.get_random_timeout()

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
                        self.ready_to_run_for_election = True

            elif self.state == State.candidate:
                time.sleep(SLEEP_TIMEOUT)
                if time.time() > self.election_timeout_point and self.ready_to_run_for_election == False:
                    lib.print_message('Election timeout - I am going to start a new term', self.id)
                    self.ready_to_run_for_election = True

    # Startup node, configure socket
    def start_serving(self):
        lib.print_message('Online in state {0}'.format(self.state), self.id)

        try:
            _thread.start_new_thread(self.heartbeat_and_election_timer_thread, ())
            self.running = True

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.settimeout(0.2)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Set the time-to-live for messages to 1 so they do not go further than the local network segment
            self.server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))

            self.multicast_listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.multicast_listener_socket.settimeout(0.2)
            self.multicast_listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            follower_address = ('', MULTICAST_PORT)
            self.multicast_listener_socket.bind(follower_address)
            # Set the time-to-live for messages to 1 so they do not go further than the local network segment
            self.multicast_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))

            # Add the socket to the multicast group
            group = socket.inet_aton(MULTICAST_ADDRESS)
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            self.server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            self.multicast_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            while self.running:

                # If you are the leader, regularly send heartbeat messages via multicast
                while self.state == State.leader and self.running is True:
                        self.do_leader_message_listening()

                # If you are a follower, listen for heartbeat messages
                while self.state == State.follower and self.running is True:
                        self.do_follower_message_listening()

                # If you are a candidate, request votes until you are elected or detect a new leader
                while self.state == State.candidate and self.running is True:
                        self.do_candidate_message_listening()

        except Exception as e1:
            lib.print_message('Exception e1: ' + str(e1), self.id)
        finally:
            sys.exit(1)

    # Listening/responding loop - candidate
    def do_candidate_message_listening(self):

        # Listen for multicast messages from other candidates and leaders (NB: Multicast senders also receive their own messages)
        while True:  # Listen until you timeout (i.e. there are no more messages)
            try:
                message, sender = self.multicast_listener_socket.recvfrom(RECV_BYTES)
                message = pickle.loads(message)
            except socket.timeout:
                break
            else:
                if message.get_term() > self.term and message.get_message_type() == MessageType.MessageType.vote_request:
                    lib.print_message('Candidate: My term is < than that of candidate ' + message.get_member_id() + ' - I am now a follower',
                                      self.id)
                    self.state = State.follower
                    self.term = message.get_term()

                elif message.get_term() >= self.term and message.get_message_type() == MessageType.MessageType.heartbeat:
                    lib.print_message(
                        'Candidate: My term is >= that of leader ' + message.get_member_id() + ' - I am now a follower',
                        self.id)
                    self.state = State.follower

        # Try to get elected leader
        if self.state == State.candidate and self.ready_to_run_for_election == True:

            #lib.print_message('I am starting a new term!', self.id)

            # Todo Should Groupview be edited?

            # Request votes through broadcast message
            self.term += 1
            votes_needed = (self.group_view.get_size() // 2) + 1
            votes_received = 1  # Start by voting for itself
            voters = []
            multicast_group = (MULTICAST_ADDRESS, MULTICAST_PORT)
            self.server_socket.sendto(
                pickle.dumps(Message.Message(self.term, MessageType.MessageType.vote_request, self.id, '')),
                multicast_group)

            # Listen for messages sent directly from followers
            while True:  # Listen until you timeout (i.e. there are no more messages)
                try:
                    message, address = self.server_socket.recvfrom(RECV_BYTES)
                    message = pickle.loads(message)
                except socket.timeout:
                    if votes_received < votes_needed:
                        #lib.print_message('I was not able to get elected. Resetting election timer...', self.id)
                        self.election_timeout_point = lib.get_random_timeout()
                        self.ready_to_run_for_election == False
                    break
                else:
                    if votes_received < votes_needed and message.get_message_type() == MessageType.MessageType.vote and message.get_term() == self.term:
                        #lib.print_message('Vote received from Member ' + message.get_member_id() + ' at ' + str(address), self.id)
                        # if not voters.__contains__(address):
                        #   voters.append(address)
                        #    votes_received += 1
                        votes_received += 1
                        if votes_received >= votes_needed:
                            lib.print_message('Sufficient votes received - I am now a leader', self.id)
                            self.state = State.leader

    # Listening/responding loop - leader
    def do_leader_message_listening(self):

        # Listen for multicast messages from candidates and other leaders (NB: Multicast senders also receive their own messages)
        while True:
            try:
                message, sender = self.multicast_listener_socket.recvfrom(RECV_BYTES)
                message = pickle.loads(message)
            except socket.timeout:
                break
            else:
                if message.get_term() > self.term and message.get_message_type() == MessageType.MessageType.heartbeat:
                    lib.print_message('Leader: my term is < than that of leader ' + message.get_member_id() + ' - I am now a follower',self.id)
                    self.state = State.follower
                    self.term = message.get_term()
                    break

        # Multicast heartbeat messages for followers
        if self.state == State.leader:
            lib.print_message('Sending heartbeats', self.id)
            try:
                leader_multicast_group = (MULTICAST_ADDRESS, MULTICAST_PORT)
                self.server_socket.sendto(
                    pickle.dumps(Message.Message(self.term, MessageType.MessageType.heartbeat, self.id, '')),
                    leader_multicast_group)
                self.num_heartbeats_sent += 1
                # TODO needs to have a per-member list of the heartbeats sent. Heartbeat must also have a sequence number.
            except Exception as e2:
                lib.print_message('Exception e2: ' + str(e2), self.id)

            # Listen for heartbeat acknowledgements from followers
            while True:
                try:
                    message, follower_address = self.server_socket.recvfrom(RECV_BYTES)
                    message = pickle.loads(message)
                except socket.timeout:
                    break
                else:
                    if message.get_message_type() == MessageType.MessageType.heartbeat_ack and message.get_term() == self.term:
                        lib.print_message('Heartbeat ACK received from Member ' + str(message.get_member_id() + ' at ' + str(follower_address)), self.id)
                        # lib.print_message('Heartbeat ACK received from ' + str(follower_address), self.id)
                        # if not self.group_view.contains(follower_address):
                        #    self.group_view.add_member(follower_address)

        # Sleep before sending more heartbeat messages
        try:
            time.sleep(SLEEP_TIMEOUT)
        except Exception as  e100:
            lib.print_message('e100: ' + str(e100), self.id)

    # Listening/responding loop - follower
    def do_follower_message_listening(self):
        while True:
            try:
                message, sender = self.multicast_listener_socket.recvfrom(RECV_BYTES)
                message = pickle.loads(message)

            except socket.timeout:
                break
            else:
                if message.get_term() > self.term and message.get_member_id() != str(self.id):
                    self.term = message.get_term()
                    self.voted = False

                if message.get_message_type() == MessageType.MessageType.heartbeat and message.get_member_id() != str(self.id):
                    self.heartbeat_received = True
                    self.server_socket.sendto(pickle.dumps(Message.Message(self.term, MessageType.MessageType.heartbeat_ack, self.id, '')), sender)

                elif message.get_message_type() == MessageType.MessageType.vote_request and message.get_member_id() != str(self.id):
                    if self.voted is False:
                        self.server_socket.sendto(pickle.dumps(Message.Message(self.term, MessageType.MessageType.vote, self.id, '')), sender)
                        self.voted = True
                        self.term = message.get_term()

    def respond_to_client_request(self, client_message):
        # TODO implement this
        pass


if __name__ == "__main__":
    member = None
    try:
        starting_state = sys.argv[1]
        starting_number_of_nodes_in_group = sys.argv[2]
        starting_id = sys.argv[3]
        member = Member(starting_state, starting_number_of_nodes_in_group, starting_id)
        _thread.start_new_thread(member.start_serving, ())

        while 1:
            sys.stdout.flush()    # Print output to console instantaneously
    except KeyboardInterrupt as main_exception:
        member.group_view.erase()
        logging.shutdown()
        exit(0)

