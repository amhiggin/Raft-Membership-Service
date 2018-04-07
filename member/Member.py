'''
    This is one of the server nodes in the RAFT distributed system. The service provided to the client will be to give them the current membership of the group.
    Each member has a group view, a mode (follower/candidate/leader), and a log of what operations it has performed.
    UDP is used for communication. Heartbeats are used to maintain the group view of every node, and message sequencing is used to detect message loss.
    Other recovery mechanisms, client service to be provided.
'''
import _thread
import pickle
import socket
import struct
import sys
import time
import uuid
import zlib

import member.Constants
from member.Constants import MULTICAST_ADDRESS, MULTICAST_PORT, CLIENT_LISTENING_PORT, CONSENSUS_PORT, \
    RECV_BYTES, SLEEP_TIMEOUT, AGREED, REMOVED

sys.path.append("../")
sys.path.append(".")
import member.GroupView as GroupView
import member.MemberLib as lib
from member import State
import Message as Message
import MessageDataType
import MessageType


class Member:

    def __init__(self, _id, _group_id, is_group_founder, partition_timer = 0):
        self.id = _id
        self.group_id = _group_id
        self.server_socket = lib.setup_server_socket(MULTICAST_ADDRESS)
        self.agreement_socket = lib.setup_agreement_socket(CONSENSUS_PORT, MULTICAST_ADDRESS)
        self.multicast_listener_socket = lib.setup_multicast_listener_socket(MULTICAST_PORT, MULTICAST_ADDRESS)
        self.client_listener_socket = None

        # Configure logging
        self.log_filename = 'MemberLogs/Group_' + str(self.group_id) + '_Member_' + str(self.id) + ".log"
        self.log_index = 0
        self.group_view = GroupView.GroupView()
        self.index_of_latest_uncommitted_log = 0
        self.index_of_latest_committed_log = 0

        # Set up state
        if is_group_founder is True:
            self.state = State.State.leader
            self.group_view.add_member(self.id)
            lib.write_to_log(self.log_filename, 'Group {0}, Log 1: Member {1} founded group'.format(self.group_id, self.id))
            self.index_of_latest_uncommitted_log += 1
            self.index_of_latest_committed_log += 1
        else:
            self.state = State.State.outsider

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
        self.message_data_type_of_previous_message = None
        self.message_data_of_previous_message = None
        self.TEST_NUMBER_OF_ACKS_SENT = 0
        self.partition_timer = partition_timer


    def do_exit_behaviour(self):
        self.group_view.erase()

    # Heartbeat timer loop - if you don't receive a heartbeat message within a certain length of time, become a candidate
    def heartbeat_and_election_timer_thread(self):
        self.heartbeat_timeout_point = lib.get_random_timeout()
        self.election_timeout_point = lib.get_random_timeout()

        while self.running is True:
            if self.state == State.State.follower:
                time.sleep(SLEEP_TIMEOUT)

                if self.heartbeat_received:
                    # Reset timeout interval
                    self.heartbeat_timeout_point = lib.get_random_timeout()
                    self.heartbeat_received = False
                else:
                    if time.time() > self.heartbeat_timeout_point:
                        lib.print_message('Heartbeat timeout - I am now a candidate', self.id)
                        self.state = State.State.candidate
                        self.ready_to_run_for_election = True
            elif self.state == State.State.candidate:
                time.sleep(SLEEP_TIMEOUT)
                if self.ready_to_run_for_election == False and time.time() > self.election_timeout_point:
                    lib.print_message('Election timeout - I am going to start a new term', self.id)
                    self.ready_to_run_for_election = True

    def network_partition_thread(self):
        time.sleep(self.partition_timer)
        member.Constants.MULTICAST_ADDRESS = member.Constants.PARTITION_MULTICAST_ADDRESS
        member.Constants.MULTICAST_PORT = member.Constants.PARTITION_MULTICAST_PORT
        self.multicast_listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.multicast_listener_socket.settimeout(0.2)
        self.multicast_listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        follower_address = ('', member.Constants.MULTICAST_PORT)
        self.multicast_listener_socket.bind(follower_address)
        # Set the time-to-live for messages to 1 so they do not go further than the local network segment
        self.multicast_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
        print('Node ' + self.id + ' is now in a network partition.\n')

    # Startup node, configure socket
    def start_serving(self):
        lib.print_message('Online in state {0}'.format(self.state), self.id)
        if self.state is State.State.leader:
            lib.print_message("Our group is available at: {0}".format(self.group_id), self.id)

        try:
            _thread.start_new_thread(self.heartbeat_and_election_timer_thread, ())
            self.running = True
            _thread.start_new_thread(member.listen_for_client, ())
            _thread.start_new_thread(member.do_follower_client_listening, ())

            # Network partition thread
            if self.partition_timer != 0:
                print('Starting network partition timer')
                _thread.start_new_thread(self.network_partition_thread, ())

            while self.running:
                # If you are the leader, regularly send heartbeat messages via multicast
                if self.state == State.State.leader and self.running is True:
                    self.do_leader_message_listening()
                # If you are a follower, listen for heartbeat messages
                if self.state == State.State.follower and self.running is True:
                    self.do_follower_message_listening()
                # If you are a candidate, request votes until you are elected or detect a new leader
                if self.state == State.State.candidate and self.running is True:
                    self.do_candidate_message_listening()
                if self.state == State.State.outsider and self.running is True:
                    self.do_outsider_message_listening()

        except Exception as e1:
            lib.print_message('Exception e1: ' + str(e1), self.id)
        finally:
            self.do_exit_behaviour()
            sys.exit(1)

    # What the leader executes if they receive an incoming client request
    # Gets consensus from the members of the group, on the current group view.
    def process_client_request_thread(self, incoming_message, client):
        decoded_message = pickle.loads(incoming_message)
        try:
            if self.state is State.State.leader:
                if decoded_message.get_message_type() is MessageType.MessageType.service_request:
                    lib.print_message("Received service request from {0}".format(client), self.id)
                    self.agreement_socket.settimeout(30)
                    self.agreement_socket.sendto(pickle.dumps(Message.Message(
                        self.group_id, self.term, MessageType.MessageType.check_group_view_consistent, None, self.id, '',
                        self.index_of_latest_uncommitted_log, self.index_of_latest_committed_log, self.group_view)),
                        (MULTICAST_ADDRESS, CONSENSUS_PORT))

                    lib.get_groupview_consensus(self)
                    lib.send_client_groupview_response(self, client)

                elif decoded_message.get_message_type() is MessageType.MessageType.client_group_delete_request:
                    lib.print_message("Received group deletion request from {0}".format(client), self.id)
                    lib.remove_members_from_group(self)
                    lib.send_client_deletion_response(self, client)
                    # TODO FIXME kill threads and step down to state outsider
        except Exception as e:
            lib.print_message("An exeption occurred when processing a client request: {0}".format(str(e)), self.id)


    # Start listening for client requests
    def listen_for_client(self):
        while True:
            try:
                self.client_listener_socket = lib.setup_client_socket(CLIENT_LISTENING_PORT, MULTICAST_ADDRESS)

                while self.running and self.state is State.State.leader:
                    incoming_message, client = self.client_listener_socket.recvfrom(RECV_BYTES)
                    try:
                        _thread.start_new_thread(self.process_client_request_thread(incoming_message, client), (incoming_message, client))
                    except Exception as consensus_response_exception:
                        lib.print_message("Exception occurred whilst getting group view consensus: {0}".format(
                            str(consensus_response_exception)), self.id)
                        self.client_listener_socket.sendto(pickle.dumps(Message.Message(
                            self.group_id, self.term, MessageType.MessageType.service_response, None, self.id, None,
                            self.index_of_latest_uncommitted_log, self.index_of_latest_committed_log, None)),
                            client)
            except Exception as client_listen_exception:
                lib.print_message("An exception occurred whilst listening for client requests: {0}".format(
                    str(client_listen_exception)), self.id)

    # Follower response to consensus-checking for a client request. The follower should verify the group
    # view if it matches theirs.
    def do_follower_client_listening(self):
        response = AGREED

        while True:
            if self.state is State.State.follower:
                try:
                    message, sender = self.agreement_socket.recvfrom(RECV_BYTES)
                    decoded_message = pickle.loads(message)

                    # Group view consensus request
                    if decoded_message.get_message_type() is MessageType.MessageType.check_group_view_consistent:
                        lib.print_message("Received group view consensus request from the leader", self.id)
                        response_type = MessageType.MessageType.check_group_view_consistent_ack
                        if decoded_message.get_group_view().exists_difference(self.group_view.get_members()):
                            response = ''
                        self.agreement_socket.sendto(pickle.dumps(Message.Message(self.group_id, self.term,
                              response_type, None, self.id, response)), (MULTICAST_ADDRESS, CONSENSUS_PORT))
                    # Group deletion request
                    elif decoded_message.get_message_type() is MessageType.MessageType.member_group_delete_request:
                        lib.print_message("Received message to delete from the leader", self.id)
                        response_type = MessageType.MessageType.member_group_delete_response
                        self.agreement_socket.sendto(pickle.dumps(Message.Message(self.group_id, self.term,
                            response_type, None, self.id, response)), (MULTICAST_ADDRESS, CONSENSUS_PORT))
                    # Group deletion confirmation/finalisation request
                    elif decoded_message.get_message_type() is MessageType.MessageType.finalise_member_removal_request:
                        lib.print_message("Received message to finalise removal from the leader", self.id)
                        # TODO remove notion of group from the follower
                        response = REMOVED
                        response_type = MessageType.MessageType.finalise_member_removal_response
                        self.agreement_socket.sendto(pickle.dumps(Message.Message(self.group_id, self.term,
                            response_type, None, self.id, response)), (MULTICAST_ADDRESS, CONSENSUS_PORT))
                except socket.timeout:
                    lib.print_message("timed out", self.id)
                    break

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
                if message.get_group_id() == self.group_id and message.get_message_type() == MessageType.MessageType.heartbeat:
                    self.server_socket.sendto(
                        pickle.dumps(Message.Message(self.group_id, self.term, MessageType.MessageType.join_request, None, self.id, 'agreed')),
                        sender)
        # Listen for direct confirmation from the leader that you have been accepted into the group
        try:
            message, address = self.server_socket.recvfrom(RECV_BYTES)
            message = pickle.loads(message)
        except socket.timeout:
            pass
        else:
            if message.get_message_type() == MessageType.MessageType.join_acceptance:
                lib.print_message('I have been accepted into a group', self.id)

                # Replicate the leader's log (which is included in the acceptance message)
                with open(self.log_filename, 'w') as log_file:
                    lib.extract_log_from_message(log_file, message)
                self.index_of_latest_uncommitted_log = message.get_index_of_latest_uncommited_log()
                self.index_of_latest_committed_log = message.get_index_of_latest_commited_log()
                self.group_view = message.get_group_view()
                self.state = State.State.follower
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
                if message.get_group_id() == self.group_id and message.get_term() > self.term and message.get_message_type() == MessageType.MessageType.vote_request:
                    lib.print_message('Candidate: My term is < than that of candidate ' + message.get_member_id() + ' - I am now a follower (and will reset my heartbeat timeout)',
                                      self.id)
                    self.heartbeat_timeout_point = lib.get_random_timeout()
                    self.state = State.State.follower
                    self.term = message.get_term()

                elif message.get_group_id() == self.group_id and message.get_term() >= self.term and message.get_message_type() == MessageType.MessageType.heartbeat:
                    lib.print_message(
                        'Candidate: My term is <= that of leader ' + message.get_member_id() + ' - I am now a follower (and will reset my heartbeat timeout)',
                        self.id)
                    self.heartbeat_timeout_point = lib.get_random_timeout()
                    self.state = State.State.follower

        # Try to get elected leader
        if self.state == State.State.candidate and self.ready_to_run_for_election == True:
            # Request votes through broadcast message
            self.term += 1
            votes_needed = (self.group_view.get_size() // 2) + 1
            votes_received = 1  # Start by voting for itself
            voters = []

            multicast_group = (MULTICAST_ADDRESS, MULTICAST_PORT)
            self.server_socket.sendto(
                pickle.dumps(Message.Message(self.group_id, self.term, MessageType.MessageType.vote_request, None, self.id, '', None, self.index_of_latest_committed_log)),
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
                            self.state = State.State.leader
                            running_for_election = False

                            # Create a new log entry, but don't commit it yet
                            self.index_of_latest_uncommitted_log += 1
                            new_log_entry = (self.index_of_latest_uncommitted_log, 'Member ' + str(self.id) + ' was elected leader')
                            self.uncommitted_log_entries.append(new_log_entry)

                            # Send the confirmation out to followers
                            self.message_data_type_of_previous_message = MessageDataType.MessageType.new_leader_elected
                            self.message_data_of_previous_message = str(self.id)

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
                if message.get_group_id() == self.group_id and message.get_term() > self.term and message.get_message_type() == MessageType.MessageType.heartbeat:
                    lib.print_message('Leader: my term is < than that of leader ' + message.get_member_id() + ' - I am now a follower',self.id)
                    self.state = State.State.follower
                    self.term = message.get_term()
                    break

        # Multicast heartbeat messages for followers
        if self.state == State.State.leader:
            try:
                leader_multicast_group = (MULTICAST_ADDRESS, MULTICAST_PORT)

                # If there are outsiders waiting to join, and there are no members to be removed
                # Prepare the other nodes to add the outsider
                removing_a_follower = False
                adding_an_outsider = False
                announcing_ascension_to_leadership = False

                if self.index_of_latest_uncommitted_log > self.index_of_latest_committed_log:
                    # Do not create a new log entry, since there already is an uncommitted entry for this log
                    if self.message_data_type_of_previous_message == MessageDataType.MessageType.removal_of_follower:
                        lib.print_message('I will retry removing a follower', self.id)
                        message_data_type = MessageDataType.MessageType.removal_of_follower
                    elif self.message_data_type_of_previous_message == MessageDataType.MessageType.addition_of_outsider:
                        lib.print_message('I will retry adding an outsider', self.id)
                        message_data_type = MessageDataType.MessageType.addition_of_outsider
                    elif self.message_data_type_of_previous_message == MessageDataType.MessageType.new_leader_elected:
                        lib.print_message('I will announce/re-announce my ascension to leadership', self.id)
                        message_data_type = MessageDataType.MessageType.new_leader_elected
                    else:
                        message_data_type = None

                    message_data = str(self.message_data_of_previous_message)

                    if message_data_type == MessageDataType.MessageType.removal_of_follower:
                        removing_a_follower = True
                    elif message_data_type == MessageDataType.MessageType.addition_of_outsider:
                        adding_an_outsider = True
                    elif message_data_type == MessageDataType.MessageType.new_leader_elected:
                        announcing_ascension_to_leadership = True

                elif len(self.unresponsive_followers) > 0:
                    message_data_type = MessageDataType.MessageType.removal_of_follower
                    self.message_data_type_of_previous_message = MessageDataType.MessageType.removal_of_follower

                    # Create new log entry, but don't commit it yet
                    self.index_of_latest_uncommitted_log += 1
                    self.uncommitted_log_entries += (self.index_of_latest_uncommitted_log, 'Member ' + self.unresponsive_followers[0] + ' left')
                    message_data = self.unresponsive_followers[0]
                    self.message_data_of_previous_message = self.unresponsive_followers[0]
                    removing_a_follower = True

                elif len(self.outsiders_waiting_to_join) > 0:
                    message_data_type = MessageDataType.MessageType.addition_of_outsider
                    self.message_data_type_of_previous_message = MessageDataType.MessageType.removal_of_follower

                    # Create new log entry, but don't commit it yet
                    self.index_of_latest_uncommitted_log += 1
                    self.uncommitted_log_entries += (self.index_of_latest_uncommitted_log, 'Member ' + self.outsiders_waiting_to_join[0] + ' joined')
                    message_data = self.outsiders_waiting_to_join[0]
                    self.message_data_of_previous_message = self.outsiders_waiting_to_join[0]
                    adding_an_outsider = True
                else:
                    message_data_type = None
                    self.message_data_type_of_previous_message = None
                    message_data = ''
                    self.message_data_of_previous_message = ''

                lib.print_message('Sending heartbeats', self.id)

                self.server_socket.sendto(
                    pickle.dumps(Message.Message(
                        self.group_id,
                        self.term,
                        MessageType.MessageType.heartbeat,
                        message_data_type,
                        self.id,
                        message_data,
                        self.index_of_latest_uncommitted_log,
                        self.index_of_latest_committed_log,
                        self.group_view)),
                    #self.group_view if self.leader_update_group_view else '')), # send group view data (sending current state instead of changes, for ease)
                    leader_multicast_group)
            except Exception as e2:
                lib.print_message('Exception e2: ' + str(e2), self.id)

            if removing_a_follower is True:
                responses_needed_to_commit_removal_of_follower = (self.group_view.get_size() // 2) + 1
            elif adding_an_outsider is True:
                responses_needed_to_commit_addition_of_outsider = (self.group_view.get_size() // 2) + 1
            elif announcing_ascension_to_leadership is True:
                responses_needed_to_commit_ascension_to_leadership = (self.group_view.get_size() // 2) + 1

            # Add self to list of responders - leader acts as if its responds to its own messages
            response_received = set()
            response_received.add(self.id)

            # Listen for heartbeat acknowledgements from followers
            while True:
                try:
                    message, member_address = self.server_socket.recvfrom(RECV_BYTES)
                    message = pickle.loads(message)
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
                            response_received.add(message.get_member_id())
                    elif message.get_message_type() == MessageType.MessageType.join_request:
                        if self.outsiders_waiting_to_join.__contains__(message.get_member_id()) is False and self.group_view.contains(message.get_member_id()) is False:
                            self.outsiders_waiting_to_join.append(message.get_member_id())
                            self.outsiders_addresses.append(member_address)
                            lib.print_message('Outsider ' + message.get_member_id() + ' added to waiting list', self.id)

            # Check to see if you got enough nodes to respond for you to add the outsider
            if removing_a_follower is True:
                if len(response_received) >= responses_needed_to_commit_removal_of_follower:
                    # Remove the follower from your group view
                    follower_to_remove = self.unresponsive_followers[0]
                    lib.print_message('Removing member {0} from group'.format(follower_to_remove), self.id)
                    self.group_view.remove_member(follower_to_remove)

                    # Commit the entry to your own log (followers will see that you have committed this entry, and will do the same - they should have an uncommitted version)
                    lib.write_to_log(self.log_filename, 'Group {0}, Log {1}: Member {2} left'.format(self.group_id, str(self.index_of_latest_uncommitted_log), follower_to_remove))
                    self.index_of_latest_committed_log += 1

                    # Remove the old follower from the list of followers to be removed
                    self.unresponsive_followers.remove(follower_to_remove)

                else:
                    lib.print_message('I did not get enough responses to commit to the removal of the follower', self.id)

            elif adding_an_outsider is True:
                if len(response_received) >= responses_needed_to_commit_addition_of_outsider:

                    # Add the new member to your own group view
                    new_member = self.outsiders_waiting_to_join[0]
                    lib.print_message('Adding member {0} to the group'.format(new_member), self.id)
                    self.group_view.add_member(new_member)

                    # Commit the entry to your own log (followers will see that you have committed this entry, and will do the same - they should have an uncommitted version)
                    lib.write_to_log(self.log_filename, 'Group {0}, Log {1}: Member {2} joined the group'.format(self.group_id, str(self.index_of_latest_uncommitted_log), new_member))
                    self.index_of_latest_committed_log += 1

                    # Message the new member to tell them they have joined
                    new_member_address = self.outsiders_addresses[0]
                    log_file = open(self.log_filename)
                    log_data = log_file.read()

                    compressed_log_data = zlib.compress(pickle.dumps(log_data, pickle.HIGHEST_PROTOCOL), 9)

                    # Send a join confirmation with the entire log index
                    # NB) What about uncommitted log entries???

                    # Send compressed log data
                    self.server_socket.sendto(pickle.dumps(Message.Message(self.term, self.group_id, MessageType.MessageType.join_acceptance, None,
                                                                           self.id, compressed_log_data,
                                                                           self.index_of_latest_uncommitted_log, self.index_of_latest_committed_log,
                                                                           self.group_view)), new_member_address)

                    # Don't need an acknowledgement from the new member - if they miss this message, they should just be removed from the group by the leader

                    # Remove the new member from the lists of outsiders
                    self.outsiders_addresses.remove(new_member_address)
                    self.outsiders_waiting_to_join.remove(new_member)

                else:
                    lib.print_message('I did not get enough responses to commit to the addition of the outsider', self.id)

            elif announcing_ascension_to_leadership is True:
                if len(response_received) >= responses_needed_to_commit_ascension_to_leadership:

                    lib.print_message('Committing my ascension to leadership', self.id)

                    # Commit the entry to your own log (followers will see that you have committed this entry, and will do the same - they should have an uncommitted version)
                    lib.write_to_log(self.log_filename, 'Group {0}, Log {1}: Member {2} was elected leader'.format(self.group_id, str(self.index_of_latest_uncommitted_log), self.id))
                    self.index_of_latest_committed_log += 1

                    self.message_data_type_of_previous_message = None

                else:
                    lib.print_message('I did not get enough responses to commit my ascension to leader', self.id)

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
                if message.get_group_id() == self.group_id: # Ignore multicast messages from other groups
                    if message.get_term() > self.term and message.get_member_id() != str(self.id):
                        self.term = message.get_term()
                        self.voted = False

                    # # updating group view of followers
                    # if message.get_message_type() == MessageType.MessageType.heartbeat and message.get_message_subtype() == MessageDataType.MessageType.group_membership_update:
                    #     self.group_view = message.get_data()

                    # A follower might be removed from the group
                    # Do not create a new log entry if this is a re-transmission from the leader (i.e. the leader already sent a message about this, but didn't get enough responses to commit it)
                    if message.get_message_type() == MessageType.MessageType.heartbeat and message.get_message_subtype() == MessageDataType.MessageType.removal_of_follower \
                            and message.get_index_of_latest_uncommited_log() > self.index_of_latest_uncommitted_log:

                        # Create a new log entry, but don't commit it yet
                        self.index_of_latest_uncommitted_log += 1
                        new_log_entry = (self.index_of_latest_uncommitted_log, 'Member ' + message.get_data() + ' left')
                        self.uncommitted_log_entries.append(new_log_entry)

                    # An outsider might be added to the group
                    # Do not create a new log entry if this is a re-transmission from the leader (i.e. the leader already sent a message about this, but didn't get enough responses to commit it)
                    elif message.get_message_type() == MessageType.MessageType.heartbeat and message.get_message_subtype() == MessageDataType.MessageType.addition_of_outsider \
                            and message.get_index_of_latest_uncommited_log() > self.index_of_latest_uncommitted_log:

                        # Create a new log entry, but don't commit it yet
                        self.index_of_latest_uncommitted_log += 1
                        new_log_entry = (self.index_of_latest_uncommitted_log, 'Member ' + message.get_data() + ' joined the group')
                        self.uncommitted_log_entries.append(new_log_entry)

                    # A new leader has been elected
                    # Do not create a new log entry if this is a re-transmission from the leader (i.e. the leader already sent a message about this, but didn't get enough responses to commit it)
                    elif message.get_message_type() == MessageType.MessageType.heartbeat and message.get_message_subtype() == MessageDataType.MessageType.new_leader_elected \
                            and message.get_index_of_latest_uncommited_log() > self.index_of_latest_uncommitted_log:

                        # Create a new log entry, but don't commit it yet
                        self.index_of_latest_uncommitted_log += 1
                        new_log_entry = (
                            self.index_of_latest_uncommitted_log, 'Member ' + message.get_data() + ' was elected leader')
                        self.uncommitted_log_entries.append(new_log_entry)

                    if message.get_message_type() == MessageType.MessageType.heartbeat and message.get_member_id() != str(self.id):
                        self.heartbeat_received = True
                        self.server_socket.sendto(pickle.dumps(Message.Message(self.group_id, self.term, MessageType.MessageType.heartbeat_ack, None, self.id, '')), sender)

                        # If the leader has committed a log entry but you have not, then commit it
                        if message.get_index_of_latest_commited_log() > self.index_of_latest_committed_log:

                            entries_to_remove = []

                            for uncommitted_log_entry in self.uncommitted_log_entries:
                                entry_id = uncommitted_log_entry[0]
                                if entry_id <= message.get_index_of_latest_commited_log():
                                    new_entry_text = 'Group {0}, Log {1}: {2}'.format(self.group_id, str(entry_id), uncommitted_log_entry[1])
                                    lib.write_to_log(self.log_filename, new_entry_text)

                                    entries_to_remove.append(uncommitted_log_entry)

                            # Remove the newly committed entries from the list of uncommitted entries
                            for entry in entries_to_remove:
                                self.uncommitted_log_entries.remove(entry)

                            self.index_of_latest_committed_log = message.get_index_of_latest_commited_log()

                            # Update your group view to match that of the leader
                            self.group_view = message.get_group_view()

                            # Check that you are still in the group
                            if self.group_view.contains(self.id) is False:
                                lib.print_message('I have been removed from the group!', self.id)
                                self.state = State.State.outsider

                    elif message.get_message_type() == MessageType.MessageType.vote_request and message.get_member_id() != str(self.id):
                        if self.voted is False and message.get_index_of_latest_commited_log() >= self.index_of_latest_committed_log:
                            self.term = message.get_term()
                            self.server_socket.sendto(pickle.dumps(Message.Message(self.group_id, self.term, MessageType.MessageType.vote, None, self.id, '')), sender)
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
                            #         self.state = State.State.outsider


if __name__ == "__main__":
    member = None
    try:
        # Configure logging
        directory = lib.create_logs_directory_if_not_exists()

        if sys.argv[1] == 'True':
            group_founder = True
        else:
            group_founder = False

        starting_id = str(uuid.uuid4())

        if group_founder:   # Group founder - set up your own group
            group_id = str(uuid.uuid4())

            # Check whether this is a demo of network partition or not
            if len(sys.argv) > 2:
                partition_timer = int(sys.argv[2])
                member = Member(starting_id, group_id, group_founder, partition_timer)
            else:
                member = Member(starting_id, group_id, group_founder, 0)

            _thread.start_new_thread(member.start_serving, ())

        else:   # Not a group founder - join all currently available groups
            # Listen for heartbeat messages from leaders
            multicast_listener_socket = lib.setup_multicast_listener_socket(MULTICAST_PORT, MULTICAST_ADDRESS)
            group_ids_found = []

            search_timeout_point = lib.get_random_timeout()

            while True:
                try:
                    message, sender = multicast_listener_socket.recvfrom(RECV_BYTES)
                    message = pickle.loads(message)
                except socket.timeout:
                    # Stop searching if at least one group to join has been found, and sufficient time has been spent searching for other groups
                    if len(group_ids_found) > 0 and time.time() > search_timeout_point:
                        break
                    else:
                        pass
                else:
                    # For each heartbeat received, start a new member instance (potential issue - multiple leaders?)
                    if message.get_message_type() == MessageType.MessageType.heartbeat:

                        group_id = message.get_group_id()

                        # Only start one member thread per group to join
                        if not group_ids_found.__contains__(group_id):
                            group_ids_found.append(group_id)

                            # Check whether this is a demo of network partition or not
                            if len(sys.argv) > 2:
                                partition_timer = int(sys.argv[2])
                                member = Member(starting_id, group_id, group_founder, partition_timer)
                            else:
                                member = Member(starting_id, group_id, group_founder, 0)

                            _thread.start_new_thread(member.start_serving, ())

        while 1:
            sys.stdout.flush()    # Print output to console instantaneously
    except Exception as main_exception:
        member.do_exit_behaviour()
        exit(0)
