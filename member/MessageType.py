from enum import Enum

class message_type(Enum):

        heartbeat = 1   # Monitor heartbeat
        service = 2     # Client service request
        outcome = 3     # Neighbour outcome query