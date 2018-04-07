'''
    Library to house all of the API methods for member servers.
'''
import datetime
import random
import time
import socket, struct
import os
import MessageType, Message
import member.Constants as constants
import pickle
import zlib

REMOVED = "removed"

GROUPVIEW_AGREEMENT_SOCKET_TIMEOUT = 1
SERVER_SOCKET_TIMEOUT = 0.2


def get_timestamp():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')


def print_message(message, id):
    print('>> {0} Member {1}:\t'.format(get_timestamp(), str(id)) + message)


# Randomised timeout delay (between 4-10 seconds) used by heartbeat messaging.
def get_random_timeout():
    return time.time() + random.uniform(4, 10)


def setup_client_socket(port, multicast_address):
    # Set up a dedicated socket, that will not time out, for listening for client requests
    client_listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    follower_address = ('', port)
    client_listener_socket.bind(follower_address)
    client_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))

    # Add the socket to the multicast group
    group = socket.inet_aton(multicast_address)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    client_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return client_listener_socket


def setup_server_socket(multicast_address):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.settimeout(SERVER_SOCKET_TIMEOUT)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Set the time-to-live for messages to 1 so they do not go further than the local network segment
    server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))

    # Add the socket to the multicast group
    group = socket.inet_aton(multicast_address)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return server_socket

def setup_agreement_socket(port, multicast_address):
    agreement_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    agreement_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    agreement_socket.bind(('', port))
    # Set the time-to-live for messages to 1 so they do not go further than the local network segment
    agreement_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))

    # Add the socket to the multicast group
    group = socket.inet_aton(multicast_address)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    agreement_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return agreement_socket


def setup_multicast_listener_socket(multicast_port, multicast_address):
    multicast_listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    multicast_listener_socket.settimeout(0.2)
    multicast_listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    follower_address = ('', multicast_port)
    multicast_listener_socket.bind(follower_address)
    # Set the time-to-live for messages to 1 so they do not go further than the local network segment
    multicast_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))

    # Add the socket to the multicast group
    group = socket.inet_aton(multicast_address)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    multicast_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return multicast_listener_socket


def get_groupview_consensus(member):
    num_agreements = 0
    while num_agreements < (calculate_required_majority(member.group_view)):
        message, responder = member.agreement_socket.recvfrom(constants.RECV_BYTES)
        decoded_message = pickle.loads(message)
        if decoded_message.get_message_type() is MessageType.MessageType.check_group_view_consistent_ack:
            if decoded_message.get_data() == constants.AGREED:
                print_message(
                    "Member {0} agreed with {1}".format(decoded_message.get_member_id(), member.group_view),
                    member.id)
                num_agreements += 1
            else:
                print_message("Member {0} disagreed with {1}".format(decoded_message.get_member_id(),
                                                                     member.group_view), member.id)
    # When exiting, consensus will have been reached


def send_client_groupview_response(member, client):
    print_message("A majority of members agreed: sending groupview to client", member.id)
    member.client_listener_socket.sendto(pickle.dumps(Message.Message(
        member.group_id, member.term, MessageType.MessageType.service_response, None, member.id, None,
        member.index_of_latest_uncommitted_log, member.index_of_latest_committed_log, member.group_view)),
        client)
    print_message("Sent group view to client {0}".format(client), member.id)


# Processes the responses to deletion requests to members of the group as part of the deletion of the group/
def remove_members_from_group(member):
    members_backup = member.group_view
    num_responses = 0
    members_to_remove = []
    respondents = []
    initial_group_size_including_leader = member.group_view.get_size()

    member.agreement_socket.settimeout(30)
    member.agreement_socket.sendto(pickle.dumps(Message.Message(
        member.group_id, member.term, MessageType.MessageType.member_group_delete_request, None, member.id, '',
        member.index_of_latest_uncommitted_log, member.index_of_latest_committed_log, member.group_view)),
        (constants.MULTICAST_ADDRESS, constants.CONSENSUS_PORT))

    while num_responses < (initial_group_size_including_leader - 1):
        message, responder = member.agreement_socket.recvfrom(constants.RECV_BYTES)
        decoded_message = pickle.loads(message)
        if (decoded_message.get_message_type() is MessageType.MessageType.member_group_delete_response) and (decoded_message.get_member_id() is not member.id):
            if decoded_message.get_data() == constants.AGREED:
                print_message("Member {0} agreed to leave the group {1}".format(decoded_message.get_member_id(),
                    member.group_view), member.id)
                members_to_remove.append(decoded_message.get_member_id())
                respondents.append(decoded_message.get_member_id())
                num_responses += 1
            else:
                print_message("Member {0} did not agree to leave the group {1}".format(decoded_message.get_member_id(),
                    member.group_id), member.id)
    if num_responses == (initial_group_size_including_leader - 1):
        try:
            safe_remove_members_from_group(member, respondents)
        except Exception as e:
            print_message("Failed to remove all group members from the group: rolling back", member.id)
            member.group_view = members_backup


# Safely remove members of the group, getting acknowledgements and storing backups for rollbacks in case of failure.
def safe_remove_members_from_group(member, respondents):
    while member.group_view.get_size() > 1:
        print_message("Checking for finalisation of removal from group", member.id)
        member.agreement_socket.sendto(pickle.dumps(Message.Message(
           member.group_id, member.term, MessageType.MessageType.finalise_member_removal_request, None, member.id, '',
           member.index_of_latest_uncommitted_log, member.index_of_latest_committed_log, member.group_view)),
           (constants.MULTICAST_ADDRESS, constants.CONSENSUS_PORT))
        response, deletion_responder = member.agreement_socket.recvfrom(constants.RECV_BYTES)
        decoded_response = pickle.loads(response)
        if decoded_response.get_data() == constants.REMOVED and respondents.__contains__(decoded_response.get_member_id()) and \
                (decoded_response.get_message_type() is MessageType.MessageType.finalise_member_removal_response):
           member.group_view.remove_member(decoded_response.get_member_id())

    # Now remove the leader too
    member.group_view.remove_member(member.id)
    if member.group_view.get_size() == 0:
        print_message("All members have successfully been removed from the group view", member.id)
    else:
        raise ValueError("There was an issue with removing members from the group for deletion")


def send_client_deletion_response(member, client):
    try:
        member.client_listener_socket.sendto(pickle.dumps(Message.Message(
            member.group_id, member.term, MessageType.MessageType.client_group_delete_response, None, member.id, constants.SUCCESS,
            member.index_of_latest_uncommitted_log, member.index_of_latest_committed_log, member.group_view)),
            client)
        print_message("Sent deletion response to client {0}".format(client), member.id)
    except Exception as e:
        print_message("Exception occurred whilst sending deletion confirmation to client: {0}".format(str(e)), member.id)


def calculate_required_majority(group_view):
    return group_view.get_size() / 2


def handle_timeout_exception(e):
    if str(e) == constants.TIMED_OUT:
        pass


def write_to_log(log_filename, message):
    log_file = open(log_filename, 'a')
    timestamp = time.strftime("%m-%d-%Y %H:%M:%S", time.gmtime())
    log_file.write(timestamp + ' ' + message + '\n')
    log_file.close()


def create_logs_directory_if_not_exists():
    directory = os.path.dirname('MemberLogs/')
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


def extract_log_from_message(log_file, message):
    compressed_data = message.get_data()
    decompressed_data = pickle.loads(zlib.decompress(compressed_data))
    log_file.write(decompressed_data)
