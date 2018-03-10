'''
    Library to house all of the API methods for member servers.
'''
import datetime
import random
import time
import sys
sys.path.append("../")


def get_timestamp():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')


def print_message(message, id):
    print('>> {0} Member {1}:\t'.format(get_timestamp(), id) + message)


# Randomised timeout delay (between 4-10 seconds) used by heartbeat messaging.
def get_random_timeout():
    return time.time() + random.uniform(4, 10)


def handle_timeout_exception(self, e):
    if str(e) == 'timed out':
        pass  # Continue
