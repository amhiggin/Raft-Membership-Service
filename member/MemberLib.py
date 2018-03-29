'''
    Library to house all of the API methods for member servers.
'''
import datetime
import random
import time
import socket, struct

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

def setup_group_view_agreement_socket(port, multicast_address):
    group_view_agreement_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    group_view_agreement_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    group_view_agreement_socket.bind(('', port))
    # Set the time-to-live for messages to 1 so they do not go further than the local network segment
    group_view_agreement_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))

    # Add the socket to the multicast group
    group = socket.inet_aton(multicast_address)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    group_view_agreement_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return group_view_agreement_socket


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


def calculate_required_majority(group_view):
    return (group_view.get_size() / 2)


def handle_timeout_exception(e):
    if str(e) == 'timed out':
        pass  # Continue
