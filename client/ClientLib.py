import socket
import time, datetime
import Message as Message
import MessageType as MessageType


def send_request():
    '''
    The client will need to be able to know where to send the request to
    '''
    print_message('Sending a request for the members of the group')
    message = Message.Message(None, MessageType.MessageType.service, '')
    # Todo send this
    pass


def get_timestamp():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')


def print_message(message):
    print('>> {0} Client:\t'.format(get_timestamp()) + message)
