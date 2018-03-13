from enum import Enum


class MessageType(Enum):

        heartbeat = 1           # Monitor heartbeat
        heartbeat_ack = 2       # Heartbeat acknowledgement
        service = 3             # Client service request
        vote_request = 4        # Candidate requesting votes
        vote = 5                # Follower vote
