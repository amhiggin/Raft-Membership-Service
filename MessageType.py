from enum import Enum


class MessageType(Enum):

        heartbeat = 1           # Monitor heartbeat
        heartbeat_ack = 2       # Heartbeat acknowledgement
        service = 3             # Client service request
        vote_request = 4        # Candidate requesting votes
        vote = 5                # Follower vote
        join_request = 6        # Request to join the group
        join_acceptance = 7     # Leader confirming to new member that they have been accepted into the group
