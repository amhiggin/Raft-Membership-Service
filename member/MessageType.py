from enum import Enum


class MessageType(Enum):

        heartbeat = 1   # Monitor heartbeat
        service = 2     # Client service request
        outcome = 3     # Neighbour outcome query
        heartbeat_ack = 4 # Heartbeat acknowledgement
        vote_request = 5 # Candidate requesting votes
        vote = 6        # Follower vote
