from enum import Enum


class MessageType(Enum):

        heartbeat = 1           # Monitor heartbeat
        heartbeat_ack = 2       # Heartbeat acknowledgement
        service_request = 3     # Client service request
        service_response = 4    # Client service response
        vote_request = 5        # Candidate requesting votes
        vote = 6                # Follower vote
        join_request = 7        # Request to join the group
        join_acceptance = 8     # Leader confirming to new member that they have been accepted into the group
        check_group_view_consistent = 9
        check_group_view_consistent_ack = 10

        # Delete request/response messages from/to client
        group_delete_request = 11
        group_delete_response = 12
