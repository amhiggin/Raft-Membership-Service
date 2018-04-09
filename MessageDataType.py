from enum import Enum


class MessageType(Enum):

        message_resend_response = 1
        group_membership_update = 2

        addition_of_outsider = 5
        removal_of_follower = 6

        new_leader_elected = 7

        new_id = 8
        message_resend_request = 3
        group_membership_update_ack = 4
