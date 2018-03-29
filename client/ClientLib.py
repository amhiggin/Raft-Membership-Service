import socket
import time, datetime
import Message as Message
import MessageType as MessageType
import pickle

MULTICAST_ADDRESS = '224.3.29.71'     # 224.0.0.0 - 230.255.255.255 -> Addresses reserved for multicasting
MULTICAST_PORT = 56789                # Port on which the group is listening for client requests
RECV_BYTES = 1024

def send_request(self_socket):
    '''
    The client will need to be able to know where to send the request to
    '''
    print_message('Sending a request for the members of the group')
    message = Message.Message(-1, MessageType.MessageType.service_request, '', None)

    multicast_group = (MULTICAST_ADDRESS, MULTICAST_PORT)
    self_socket.sendto(pickle.dumps(message), multicast_group)

    try:
        message, address = self_socket.recvfrom(RECV_BYTES)
        message = pickle.loads(message)
        if message.get_message_type() == MessageType.MessageType.service_response:
            group_view = message.get_group_view()
            return group_view.get_members()
    except Exception as e1:
        print_message("An exception occurred while waiting for response from group: {0}".format(str(e1)))
    return None


def get_timestamp():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')


def print_message(message):
    print('>> {0} Client:\t'.format(get_timestamp()) + message)