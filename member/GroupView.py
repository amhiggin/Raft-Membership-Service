'''
This is the view of the membership of the group that each member has at any given time.
The member should update this groupview as part of the protocol.
'''


class GroupView:
    # Must have an ordered list of members.
    # This means that two lists can be equated to see if the same sequence of changes has happened to both.

    def __init__(self):
        self.members = {}

    # Add a member to the group view
    def add_member(self, new_member):
        self.members.items().append(new_member)

    # Remove a member from the group view
    def remove_member(self, old_member):
        self.members.items().remove(old_member)

    def get_group_view(self):
        return self.members

    def get_group_size(self):
        return self.members.__len__()