from enum import Enum

class message_type(Enum):

        heartbeat = 1   # Monitor heartbeat
        service = 2     # Client service request
        outcome = 3     # Neighbour outcome query
        heartbeat_ack = 4 # Heartbeat acknowledgement
        vote_request = 5 # Candidate requesting votes
        vote = 6        # Follower vote
        new_leader = 7  # Candidate announces itself as the new leader
