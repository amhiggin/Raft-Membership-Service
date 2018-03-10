'''
An enum for the states that members of the group can be in.
Each Member can be one of (i) a follower, (ii) a candidate or (iii) a leader.
'''

from enum import Enum


class State(Enum):

        follower = 'follower'    # Follower - default state
        candidate = 'candidate'   # Candidate for election
        leader = 'leader'       # Leader of group

        @classmethod
        def has_value(cls, value):
                return any(value == item.value for item in cls)