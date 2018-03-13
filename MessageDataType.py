from enum import Enum

class MessageType(Enum):

        # TODO use these later once the sequence numbers are done correctly
        # Heartbeat sub-messages
        message_resend_response = 1
        group_membership_update = 2

        # Heartbeat ACK sub-messages
        new_id = 8
        message_resend_request = 3
        group_membership_update_ack = 4
