'''
An enum for the states that members of the group can be in.
Each Member can be one of (i) a follower, (ii) a candidate, (iii) a leader or (iv) an outsider.
'''

from enum import Enum


class State(Enum):

        follower = 'follower'    # Follower - member of the group
        candidate = 'candidate'   # Candidate for election
        leader = 'leader'       # Leader of group

        outsider = 'outsider'   # Not a member of the group

        @classmethod
        def has_value(cls, value):
                return any(value == item.value for item in cls)
