'''
API methods for member servers
'''

import time, MessageType


def get_timestamp():
    return time.strftime("%a %c %Y")


def print_message(message, id):
    print('Member {0}:\t' + message + '\n'.format(id))


def send_heartbeat(connection):
    # TODO send this message: needs to know the monitor node, and fallback to election if not present
    construct_message(MessageType.heartbeat, get_timestamp())


def respond_to_message(data_received):
    if data_received.contains('heartbeat'):
        send_heartbeat()
        return True
    else:
        pass  # Client service request: depends on what service is being implemented
    return None


def construct_message(msg_type, message):
    if msg_type == MessageType.heartbeat:
        return 'HEARTBEAT-ACK-' + str(message)
    else:
        # TODO implement the other message types
        return None


def register_member():
    '''
    TODO register this member and give them some initialisation info
    This might be a copy of the log or something similar
    '''
    return None


def request_group_view():
    '''
    TODO enable requesting of the current group view from the monitor node.
    Failure mechanism needs to be able to fallback to election if there is no monitor present.
    This will involve a timeout on the request, an election, and then either resending the request or the creation of the group view (if this node is the leader).
    '''
    return None


def request_current_log():
    ''' TODO enable requesting of the current log from the monitor node
    The node will need a log, and then need to make this a replica of the monitors log (?)
    Failure mechanism here too
    '''
    return None