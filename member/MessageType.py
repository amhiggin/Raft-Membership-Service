'''
An enum for the types of messages that can be sent/received by members of the group.
'''

from enum import Enum


class MessageType(Enum):

        heartbeat = 1   # Monitor heartbeat
        service = 2     # Client service request
        outcome = 3     # Neighbour outcome query ('what happened after I failed?')
        vote = 4        # A vote message