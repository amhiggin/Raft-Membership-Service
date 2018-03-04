'''
An enum for the states that members of the group can be in.
Each Member can be one of (i) a follower, (ii) a candidate or (iii) a leader.
'''

from enum import Enum


class State(Enum):

        follower = 1    # Follower - default state
        candidate = 2   # Candidate for election
        leader = 3       # Leader of group