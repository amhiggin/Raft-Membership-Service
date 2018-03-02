'''
An enum for the states that members of the group can be in.
'''

from enum import Enum


class State(Enum):

        follower = 1    # Follower - default state
        candidate = 2   # Candidate for election
        leader = 3      # Leader of group