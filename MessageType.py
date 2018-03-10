from enum import Enum


class MessageType(Enum):

        heartbeat = 1           # Monitor heartbeat
        heartbeat_ack = 2       # Heartbeat acknowledgement
        service = 3             # Client service request
        vote_request = 4        # Candidate requesting votes
        vote = 5                # Follower vote

        '''
        Sub-messages (encapsulated in heartbeats/heartbeat ACKs
        '''

        # TODO use these later once the sequence numbers are done correctly
        # Heartbeat sub-messages
        #message_resend_response = 6
        #group_membership_update = 7

        # Heartbeat ACK sub-messages
        #new_id = 8
        #message_resend_request = 9
        #group_membership_update_ack = 10
