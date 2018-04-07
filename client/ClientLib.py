import socket
import time, datetime
import Message as Message
import MessageType as MessageType
import pickle
import uuid

MULTICAST_ADDRESS = '224.3.29.71'     # 224.0.0.0 - 230.255.255.255 -> Addresses reserved for multicasting
MULTICAST_PORT = 56789                # Port on which the group is listening for client requests
RECV_BYTES = 1024
TIMEOUT_PERIOD_SECONDS = 30


def setup_up_socket(socket_port):
    # Set up client socket
    self_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self_socket.bind(('', socket_port))
    self_socket.settimeout(TIMEOUT_PERIOD_SECONDS)
    return self_socket


def send_service_request(self_socket, group_address):
    print_message('Sending a request for the members of group {0}'.format(group_address))
    message = Message.Message(None, -1, MessageType.MessageType.service_request, '', None, None)
    multicast_group = (group_address, MULTICAST_PORT)

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
    message = Message.Message(None, -1, MessageType.MessageType.group_delete_request, '', None, None)
    multicast_group = (group_address, MULTICAST_PORT)

    try:
        self_socket.sendto(pickle.dumps(message), multicast_group)
        message, address = self_socket.recvfrom(RECV_BYTES)
        message = pickle.loads(message)
        if message.get_message_type() == MessageType.MessageType.group_delete_response:
            group_view = message.get_group_view()
            if group_view is not None:
                return group_view.get_members()
    except Exception as e1:
        print_message("An exception occurred while waiting for response from group: {0}".format(str(e1)))
    return None


def get_timestamp():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')


def print_message(message):
    print('>> {0} Client:\t'.format(get_timestamp()) + message)
