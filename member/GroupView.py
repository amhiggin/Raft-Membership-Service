'''
This is the view of the membership of the group that each member has at any given time.
The member should update this groupview as part of the protocol.
The group view is updated with no more than one change at a time - either an addition or removal of a member.
Using a list ensures ordering whilst also allowing for arbitrary removal of nodes at any position.
Checks are in place to prevent duplicates from being added.
'''


class GroupView:

    def __init__(self):
        self.members = []

    # Add a member to the group view
    def add_member(self, new_member):
        if not self.members.__contains__(new_member):
            self.members.append(new_member)
        else:
            # TODO Pooja this may need to be added to the log
            print('Member {0} was already in the group view - did not add duplicate.'.format(new_member.name))

    # Remove a member from the group view
    def remove_member(self, old_member):
        if self.members.contains(old_member):
            self.members.remove(old_member)
        else:
            # TODO Pooja this may need to be added to the log
            print('Member {0} was not in the group view - did not attempt removal.'.format(old_member.name))

    def get_group_view(self):
        return self.members

    def get_group_size(self):
        return self.members.__len__()