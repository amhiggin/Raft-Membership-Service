import datetime
import pickle
import socket
import struct
import time

import Message as Message
import MessageType as MessageType

GROUPS_INFO = dict()

MULTICAST_ADDRESS = '224.3.29.71'     # 224.0.0.0 - 230.255.255.255 -> Addresses reserved for multicasting
MULTICAST_PORT = 56789                # Port on which the group is listening for client requests
RECV_BYTES = 1024
TIMEOUT_PERIOD_SECONDS = 60           # Long timeout to allow for deletion confirmation to be given
GROUP_PORT = 56789
GROUP_ADDRESS = '224.3.29.71'
SUCCESS = "success"
MULTIGROUP_MULTICAST_ADDRESS = '224.3.29.73'
MULTIGROUP_MULTICAST_PORT = 45680

TIMEOUT_LISTEN_FOR_GROUPS = 3


def setup_up_socket(socket_port):
    # Set up client socket
    self_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self_socket.bind(('', socket_port))
    self_socket.settimeout(TIMEOUT_PERIOD_SECONDS)
    return self_socket


def get_group_listener_socket():
    multicast_listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    multicast_listener_socket.settimeout(0.2)
    multicast_listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    follower_address = ('', MULTIGROUP_MULTICAST_PORT)
    multicast_listener_socket.bind(follower_address)
    # Set the time-to-live for messages to 1 so they do not go further than the local network segment
    multicast_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))

    # Add the socket to the multicast group
    group = socket.inet_aton(MULTIGROUP_MULTICAST_ADDRESS)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    multicast_listener_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return multicast_listener_socket


def send_service_request(self_socket, group_id):
    group_info = GROUPS_INFO[group_id]
    print_message('Sending a request for the members of group {0}'.format(group_id))
    message = Message.Message(None, -1, MessageType.MessageType.service_request, '', None, None)
    multicast_group = (group_info["address"], GROUP_PORT)

    try:
        self_socket.sendto(pickle.dumps(message), multicast_group)
        message, address = self_socket.recvfrom(RECV_BYTES)
        message = pickle.loads(message)
        if message.get_message_type() == MessageType.MessageType.service_response:
            group_view = message.get_group_view()
            if group_view is not None:
                return group_view.get_members()
    except Exception as e1:
        print_message("An exception occurred while waiting for response from group: {0}".format(str(e1)))
    return None


def send_delete_request(self_socket, group_address):
    print_message('Sending a request to delete group {0}'.format(group_address))
    message = Message.Message(None, -1, MessageType.MessageType.client_group_delete_request, '', None, None)
    multicast_group = (GROUP_ADDRESS, GROUP_PORT)

    try:
        self_socket.sendto(pickle.dumps(message), multicast_group)
        message, address = self_socket.recvfrom(RECV_BYTES)
        decoded_message = pickle.loads(message)
        if decoded_message.get_message_type() == MessageType.MessageType.client_group_delete_response and \
                decoded_message.get_data() == SUCCESS:
            return SUCCESS
        else:
            return None
    except Exception as e1:
        print_message("An exception occurred while waiting for response from group: {0}".format(str(e1)))
    return None


def listen_for_groups(group_listener_socket):
    groups = set()
    GROUPS_INFO.clear()
    # leader_responses = [(MULTICAST_ADDRESS, MULTICAST_PORT)]
    search_timeout_point = get_timeout()
    print_message("Listening for all available groups...")
    while True:
        try:
            if time.time() > search_timeout_point:
                print_message("Finished listening for all groups.")
                break
            message, sender = group_listener_socket.recvfrom(RECV_BYTES)
            message = pickle.loads(message)
        except socket.timeout:
            pass
        else:
            multicast_address, multicast_port = message.get_group_address()
            group_id = message.get_group_id()
            if group_id in groups:
                continue
            else:
                print_message("New group found!")
                groups.add(group_id)
                GROUPS_INFO[str(group_id)] = {
                    "address":multicast_address,
                    "port":multicast_port
                }
    return groups


def get_timeout():
    return time.time() + TIMEOUT_LISTEN_FOR_GROUPS


def get_timestamp():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')


def print_message(message):
    print('>> {0} Client:\t'.format(get_timestamp()) + message)
