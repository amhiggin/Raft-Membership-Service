'''
    This is one of the server nodes in the RAFT distributed system. The service provided to the client will be to give them the current membership of the group.
    Each member has a group view, a mode (follower/candidate/leader), and a log of what operations it has performed.
    UDP is used for communication. Heartbeats are used to maintain the group view of every node, and message sequencing is used to detect message loss.
    Other recovery mechanisms, client service to be provided.
'''

import _thread, sys
import socket
import MemberLib as lib
#from DistributedManagementSystem import MessageType
from MessageType import MessageType
import GroupView as GroupView
from State import State
import time
import struct
import logging
import pickle
#from DistributedManagementSystem import Message as Message
import Message as Message
#from DistributedManagementSystem import MessageDataType
import MessageDataType
import os

sys.path.append("../")
sys.path.append(".")

'''  Server constants '''
SERVER_PORT = 45678  # Review
DEFAULT_STATE = State.follower
MULTICAST_ADDRESS = '224.3.29.71'     # 224.0.0.0 - 230.255.255.255 -> Addresses reserved for multicasting
MULTICAST_PORT = 45678
PARTITION_MULTICAST_PORT = 45679
PARTITION_MULTICAST_ADDRESS = '224.3.29.72'

''' Generic constants '''
RECV_BYTES = 1024
SLEEP_TIMEOUT = 1


class Member:

    def __init__(self,_id, group_founder, partition_timer=0):
        self.id = _id
        self.server_socket = None

        # Configure logging
        self.log_filename = "MemberLogs/Member_" + str(self.id) + ".log"
        logging.basicConfig(filename = self.log_filename, level=logging.DEBUG,format="%(asctime)s: %(message)s")
        logging.FileHandler(self.log_filename, mode='w')  # Overwrite previous version of log (if it exists)
        self.log_index = 0

        self.group_view = GroupView.GroupView()

        self.index_of_latest_uncommitted_log = 0
        self.index_of_latest_committed_log = 0

        if group_founder is True:
            self.state = State.leader
            self.group_view.add_member(self.id)
            logging.info('Member {0} founded group'.format(self.id))
            self.index_of_latest_uncommitted_log += 1
            self.index_of_latest_committed_log += 1
        else:
            self.state = State.outsider

        self.multicast_listener_socket = None
        self.heartbeat_timeout_point = None
        self.election_timeout_point = None
        self.heartbeat_received = False
        self.ready_to_run_for_election = False
        self.leader_update_group_view = False
        self.running = None
        self.term = 0
        self.voted = False

        self.outsiders_waiting_to_join = []
        self.outsiders_addresses = []

        self.unresponsive_followers = []

        self.uncommitted_log_entries = []

        self.TEST_NUMBER_OF_ACKS_SENT = 0

        self.partition_timer = partition_timer
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
                if self.ready_to_run_for_election == False and time.time() > self.election_timeout_point:
                    lib.print_message('Election timeout - I am going to start a new term', self.id)
                    self.ready_to_run_for_election = True

    def network_partition_thread(self):
        print('Node ' + self.id + ' is sleeping.\n')
        time.sleep(self.partition_timer)
        print('Node ' + self.id + ' is awake.\n')
        #self.multicast_listener_socket.close()
        global MULTICAST_ADDRESS
        global MULTICAST_PORT
        global PARTITION_MULTICAST_ADDRESS
        global PARTITION_MULTICAST_PORT
        #print('Node multicast port closed.\n')
        MULTICAST_ADDRESS = PARTITION_MULTICAST_ADDRESS
        MULTICAST_PORT = PARTITION_MULTICAST_PORT
        print('Node multicast port and address changed.\n')
        self.multicast_listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.multicast_listener_socket.settimeout(0.2)
        self.multicast_listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        follower_address = ('', MULTICAST_PORT)
        self.multicast_listener_socket.bind(follower_address)
        # Set the time-to-live for messages to 1 so they do not go further than the local network segment
        self.multicast_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
        print('Node partitioned.\n')

    # Startup node, configure socket
    def start_serving(self):

        # Configure logging
        directory = os.path.dirname('MemberLogs/')
        if not os.path.exists(directory):
            os.makedirs(directory)

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

            #network partition thread
            if self.partition_timer != 0:
                print('Starting network partition timer')
                _thread.start_new_thread(self.network_partition_thread, ())

            
            while self.running:

                # If you are the leader, regularly send heartbeat messages via multicast
                if self.state == State.leader and self.running is True:
                    self.do_leader_message_listening()

                # If you are a follower, listen for heartbeat messages
                if self.state == State.follower and self.running is True:
                    self.do_follower_message_listening()

                # If you are a candidate, request votes until you are elected or detect a new leader
                if self.state == State.candidate and self.running is True:
                    self.do_candidate_message_listening()

                if self.state == State.outsider and self.running is True:
                    self.do_outsider_message_listening()

        except Exception as e1:
            lib.print_message('Exception e1: ' + str(e1), self.id)
        finally:
            sys.exit(1)

    # Listening/responding loop - outsider
    def do_outsider_message_listening(self):
        # Listen for heartbeat messages from leaders
        while True:
            try:
                message, sender = self.multicast_listener_socket.recvfrom(RECV_BYTES)
                message = pickle.loads(message)
            except socket.timeout:
                break
            else:
                if message.get_message_type() == MessageType.MessageType.heartbeat:

                     self.server_socket.sendto(
                         pickle.dumps(Message.Message(self.term, MessageType.MessageType.join_request, None, self.id, '')),
                         sender)

        # Listen for direct confirmation from the leader that you have been accepted into the group
        try:
            message, address = self.server_socket.recvfrom(RECV_BYTES)
            message = pickle.loads(message)
        except socket.timeout:
            pass
        else:
            if message.get_message_type() == MessageType.MessageType.join_acceptance:
                    lib.print_message('I have been accepted into the group', self.id)

                    # Replicate the leader's log (which is included in the acceptance message)
                    with open(self.log_filename, 'w') as log_file:
                        log_file.write(message.get_data())

                    self.index_of_latest_uncommitted_log = message.get_index_of_latest_uncommited_log()
                    self.index_of_latest_committed_log = message.get_index_of_latest_commited_log()

                    self.group_view = message.get_group_view()
                    lib.print_message('My new group view is ' + str(self.group_view.get_members()), self.id)

                    self.state = State.follower
                    self.heartbeat_timeout_point = lib.get_random_timeout()


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
                    lib.print_message('Candidate: My term is < than that of candidate ' + message.get_member_id() + ' - I am now a follower (and will reset my heartbeat timeout)',
                                      self.id)
                    self.heartbeat_timeout_point = lib.get_random_timeout()
                    self.state = State.follower
                    self.term = message.get_term()

                elif message.get_term() >= self.term and message.get_message_type() == MessageType.MessageType.heartbeat:
                    lib.print_message(
                        'Candidate: My term is <= that of leader ' + message.get_member_id() + ' - I am now a follower (and will reset my heartbeat timeout)',
                        self.id)
                    self.heartbeat_timeout_point = lib.get_random_timeout()
                    self.state = State.follower

        # Try to get elected leader
        if self.state == State.candidate and self.ready_to_run_for_election == True:

            # lib.print_message('I am starting a new term!', self.id)

            # Todo Should Groupview be edited?


            # Request votes through broadcast message
            self.term += 1
            votes_needed = (self.group_view.get_size() // 2) + 1
            votes_received = 1  # Start by voting for itself
            voters = []

            multicast_group = (MULTICAST_ADDRESS, MULTICAST_PORT)
            self.server_socket.sendto(
                pickle.dumps(Message.Message(self.term, MessageType.MessageType.vote_request, None, self.id, '')),
                multicast_group)

            # Listen for votes until your election time is up, or you receive enough votes to become leader
            running_for_election = True
            self.election_timeout_point = lib.get_random_timeout()
            # Listen for messages sent directly from followers
            while running_for_election:  # Listen until you timeout (i.e. there are no more messages)
                try:
                    message, address = self.server_socket.recvfrom(RECV_BYTES)
                    message = pickle.loads(message)
                except socket.timeout:
                    if time.time() > self.election_timeout_point:
                        running_for_election = False
                else:
                    if message.get_message_type() == MessageType.MessageType.vote and message.get_term() == self.term:
                        lib.print_message('Vote received from Member ' + message.get_member_id() + ' at ' + str(address), self.id)
                        # if not voters.__contains__(address):
                        #   voters.append(address)
                        #    votes_received += 1
                        votes_received += 1

                        if votes_received >= votes_needed:
                            lib.print_message('Sufficient votes received - I am now a leader', self.id)
                            self.state = State.leader
                            running_for_election = False

                    if time.time() > self.election_timeout_point:
                        running_for_election = False

            if votes_received < votes_needed:
                lib.print_message('I was not able to get elected. Resetting election timer...', self.id)
                self.ready_to_run_for_election = False
                self.election_timeout_point = lib.get_random_timeout()

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

            try:
                leader_multicast_group = (MULTICAST_ADDRESS, MULTICAST_PORT)

                # If there are outsiders waiting to join, and there are no members to be removed
                # Prepare the other nodes to add the outsider

                removing_a_follower = False
                adding_an_outsider = False

                if len(self.unresponsive_followers) > 0:
                    messageDataType = MessageDataType.MessageType.removal_of_follower

                    # Create new log entry, but don't commit it yet
                    self.index_of_latest_uncommitted_log += 1
                    self.uncommitted_log_entries += (self.index_of_latest_uncommitted_log, 'Member ' + self.unresponsive_followers[0] + ' left')
                    messageData = self.unresponsive_followers[0]
                    removing_a_follower = True
                elif len(self.outsiders_waiting_to_join) > 0:
                    messageDataType = MessageDataType.MessageType.addition_of_outsider

                    # Create new log entry, but don't commit it yet
                    self.index_of_latest_uncommitted_log += 1
                    self.uncommitted_log_entries += (self.index_of_latest_uncommitted_log, 'Member ' + self.outsiders_waiting_to_join[0] + ' joined')
                    messageData = self.outsiders_waiting_to_join[0]
                    adding_an_outsider = True
                else:
                    messageDataType = None
                    messageData = ''

                #messageDataType = MessageDataType.MessageType.group_membership_update if self.leader_update_group_view else None # if leader group view has changed

                lib.print_message('Sending heartbeats', self.id)

                self.server_socket.sendto(
                    pickle.dumps(Message.Message(
                        self.term,
                        MessageType.MessageType.heartbeat,
                        messageDataType,
                        self.id,
                        messageData,
                        self.index_of_latest_uncommitted_log,
                        self.index_of_latest_committed_log,
                        self.group_view)),
                        #self.group_view if self.leader_update_group_view else '')), # send group view data (sending current state instead of changes, for ease)
                    leader_multicast_group)
                # TODO needs to have a per-member list of the heartbeats sent. Heartbeat must also have a sequence number.
            except Exception as e2:
                lib.print_message('Exception e2: ' + str(e2), self.id)

            if removing_a_follower is True:
                responses_needed_to_commit_removal_of_follower = (self.group_view.get_size() // 2) + 1
            elif adding_an_outsider is True:
                responses_needed_to_commit_addition_of_outsider = (self.group_view.get_size() // 2) + 1

            # Add self to list of responders - leader acts as if its responds to its own messages
            response_received = set(self.id)

            # Listen for heartbeat acknowledgements from followers
            while True:
                try:
                    message, member_address = self.server_socket.recvfrom(RECV_BYTES)
                    message = pickle.loads(message)
                    if self.unresponsive_followers.__contains__(message.get_member_id()) is False:  # Disregard acknowledgements from followers that have been marked for removal
                        response_received.add(message.get_member_id())
                except socket.timeout:
                    # Only check for unresponsive followers if you don't have any marked for removal at the moment - doing otherwise might cause issues that aren't yet accounted for
                    if len(self.unresponsive_followers) == 0:
                        # Check for members that didn't respond - start to remove them with the next heartbeat
                        self.unresponsive_followers = self.group_view.get_difference(response_received)
                        if len(self.unresponsive_followers) > 0:
                            lib.print_message('I have unresponsive followers to be removed: ' + str(self.unresponsive_followers), self.id)
                    break
                else:
                    if message.get_message_type() == MessageType.MessageType.heartbeat_ack and self.group_view.contains(message.get_member_id()) is False:
                        lib.print_message('An outsider thinks they are a follower - they are being ignored', self.id)
                    elif message.get_message_type() == MessageType.MessageType.heartbeat_ack and message.get_term() == self.term:
                        if self.unresponsive_followers.__contains__(message.get_member_id()) is False:  # Disregard acknowledgements from followers that have been marked for removal
                            lib.print_message('Heartbeat ACK received from Member ' + str(message.get_member_id() + ' at ' + str(member_address)), self.id)

                    elif message.get_message_type() == MessageType.MessageType.join_request:
                        #lib.print_message('Join request received from Member ' + str(message.get_member_id() + ' at ' + str(member_address)), self.id)
                        if self.outsiders_waiting_to_join.__contains__(message.get_member_id()) is False and self.group_view.contains(message.get_member_id()) is False:
                            self.outsiders_waiting_to_join.append(message.get_member_id())
                            self.outsiders_addresses.append(member_address)
                            lib.print_message('Outsider ' + message.get_member_id() + ' added to waiting list', self.id)

            # Check to see if you got enough nodes to respond for you to add the outsider
            if removing_a_follower is True:
                if len(response_received) >= responses_needed_to_commit_removal_of_follower:
                    # Remove the follower from your group view
                    lib.print_message('Removing follower from group', self.id)
                    follower_to_remove = self.unresponsive_followers[0]
                    self.group_view.remove_member(follower_to_remove)

                    # Commit the entry to your own log (followers will see that you have committed this entry, and will do the same - they should have an uncommitted version)
                    logging.info('Member {0} left'.format(follower_to_remove))
                    self.index_of_latest_committed_log += 1

                    # Remove the old follower from the list of followers to be removed
                    self.unresponsive_followers.remove(follower_to_remove)

                else:
                    lib.print_message('I did not get enough responses to commit to the removal of the follower', self.id)

            elif adding_an_outsider is True:
                if len(response_received) >= responses_needed_to_commit_addition_of_outsider:

                    # Add the new member to your own group view
                    lib.print_message('Adding new member to the group', self.id)
                    new_member = self.outsiders_waiting_to_join[0]
                    self.group_view.add_member(new_member)

                    # Commit the entry to your own log (followers will see that you have committed this entry, and will do the same - they should have an uncommitted version)
                    logging.info('Member {0} joined the group'.format(new_member))
                    self.index_of_latest_committed_log += 1

                    # Message the new member to tell them they have joined
                    new_member_address = self.outsiders_addresses[0]
                    log_file = open(self.log_filename)
                    log_data = log_file.read()

                    # Send a join confirmation with the entire log index
                    # NB) What about uncommitted log entries???
                    self.server_socket.sendto(pickle.dumps(Message.Message(self.term, MessageType.MessageType.join_acceptance, None, self.id, log_data,
                                                                           self.index_of_latest_uncommitted_log, self.index_of_latest_committed_log,
                                                                           self.group_view)), new_member_address)

                    # Don't need an acknowledgement from the new member - if they miss this message, they should just be removed from the group by the leader

                    # Remove the new member from the lists of outsiders
                    self.outsiders_addresses.remove(new_member_address)
                    self.outsiders_waiting_to_join.remove(new_member)

                else:
                    lib.print_message('I did not get enough responses to commit to the addition of the outsider', self.id)

        # Sleep before sending more heartbeat messages
        try:
            time.sleep(SLEEP_TIMEOUT)
        except Exception as e100:
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

                # # updating group view of followers
                # if message.get_message_type() == MessageType.MessageType.heartbeat and message.get_message_subtype() == MessageDataType.MessageType.group_membership_update:
                #     self.group_view = message.get_data()

                # A follower might be removed from the group
                if message.get_message_type() == MessageType.MessageType.heartbeat and message.get_message_subtype() == MessageDataType.MessageType.removal_of_follower:
                    # Create a new log entry, but don't commit it yet
                    self.index_of_latest_uncommitted_log += 1
                    new_log_entry = (self.index_of_latest_uncommitted_log, 'Member ' + message.get_data() + ' left')
                    self.uncommitted_log_entries.append(new_log_entry)

                # An outsider might be added to the group
                elif message.get_message_type() == MessageType.MessageType.heartbeat and message.get_message_subtype() == MessageDataType.MessageType.addition_of_outsider:

                    # Create a new log entry, but don't commit it yet
                    self.index_of_latest_uncommitted_log += 1
                    new_log_entry = (self.index_of_latest_uncommitted_log, 'Member ' + message.get_data() + ' joined the group')
                    self.uncommitted_log_entries.append(new_log_entry)

                if message.get_message_type() == MessageType.MessageType.heartbeat and message.get_member_id() != str(self.id):
                    self.heartbeat_received = True
                    if self.TEST_NUMBER_OF_ACKS_SENT == 3 and self.id == str(3):    # Member 3 only
                        lib.print_message('FAILURE TEST: I am not going to send this ack', self.id)
                    else:
                        self.server_socket.sendto(pickle.dumps(Message.Message(self.term, MessageType.MessageType.heartbeat_ack, None, self.id, '')), sender)

                    self.TEST_NUMBER_OF_ACKS_SENT += 1

                    # If the leader has committed a log entry but you have not, then commit it
                    if message.get_index_of_latest_commited_log() > self.index_of_latest_committed_log:

                        entries_to_remove = []

                        for uncommitted_log_entry in self.uncommitted_log_entries:
                            entry_id = uncommitted_log_entry[0]
                            if entry_id <= message.get_index_of_latest_commited_log():
                                new_entry_text = uncommitted_log_entry[1]
                                logging.info(new_entry_text)

                                entries_to_remove.append(uncommitted_log_entry)

                        # Remove the newly committed entries from the list of uncommitted entries
                        for entry in entries_to_remove:
                            self.uncommitted_log_entries.remove(entry)

                        self.index_of_latest_committed_log = message.get_index_of_latest_commited_log()

                        # Update your group view to match that of the leader
                        self.group_view = message.get_group_view()
                        lib.print_message('My new group view is ' + str(self.group_view.get_members()), self.id)

                        # Check that you are still in the group
                        if self.group_view.contains(self.id) is False:
                            lib.print_message('I have been removed from the group!', self.id)
                            self.state = State.outsider

                elif message.get_message_type() == MessageType.MessageType.vote_request and message.get_member_id() != str(self.id):
                    if self.voted is False:
                        self.term = message.get_term()
                        self.server_socket.sendto(pickle.dumps(Message.Message(self.term, MessageType.MessageType.vote, None, self.id, '')), sender)
                        self.voted = True

        # # Listen for direct confirmation from the leader that you have been removed from the group
        # try:
        #     message, address = self.server_socket.recvfrom(RECV_BYTES)
        #     message = pickle.loads(message)
        # except socket.timeout:
        #     pass
        # else:
        #     if message.get_message_type() == MessageType.MessageType.removal:
        #         lib.print_message('I have been removed from the group', self.id)
        #         self.state = State.outsider

    def respond_to_client_request(self, client_message):
        # TODO implement this
        pass


if __name__ == "__main__":
    member = None
    try:
        if sys.argv[1] == 'True':
            group_founder = True
        else:
            group_founder = False

        starting_id = sys.argv[2]
        partition_timer = int(sys.argv[3])
        #print('Node ' + starting_id + ': partition timer = ' + partition_timer+'.\n')
        member = Member(starting_id, group_founder, partition_timer)
        _thread.start_new_thread(member.start_serving, ())

        while 1:
            sys.stdout.flush()    # Print output to console instantaneously
    except KeyboardInterrupt as main_exception:
        member.group_view.erase()
        logging.shutdown()
        exit(0)

