'''
Library to house all of the API methods for member servers
'''

import time
import MessageType


def get_timestamp():
    return time.strftime("%a %c %Y")


def print_message(message, id):
    print('Member {}:\t'.format(id) + message + '\n')


def send_heartbeat(connection):
    connection.sendall(construct_message(MessageType.heartbeat, get_timestamp()).encode())


def respond_to_message(connection, data_received):
    if data_received.contains('heartbeat'):
        send_heartbeat(connection)
        return True
    else:
        pass  # Client service request: depends on what service is being implemented
    return None


def construct_message(msg_type, message):
    if msg_type == MessageType.heartbeat:
        return 'HEARTBEAT-ACK-' + str(message)
    else:
        return None
