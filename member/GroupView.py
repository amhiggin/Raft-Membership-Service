'''
    This is the view of the membership of the group that each member has at any given time.
    The member should update this groupview as part of the protocol.
    The group view is updated with no more than one change at a time - either an addition or removal of a member.
    Using a list ensures ordering whilst also allowing for arbitrary removal of nodes at any position.
    Checks are in place to prevent duplicates from being added.
'''
import logging, sys
sys.path.append("../")
import MemberLib as lib


logging.basicConfig(
    filename="DistributedManagementSystem.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s"
)


class GroupView(object):

    def __init__(self):
        self.members = []

    # Add a member to the group view
    def add_member(self, new_member_id): #new_member):
        if not self.contains(new_member_id):
            self.members.append(new_member_id)
            print('>> {0}\t Member {1} joined'.format(lib.get_timestamp(), new_member_id))
            logging.info('Member {0} joined'.format(new_member_id))
        else:
            print('>> {0}\t Member {1} was already in my group view - did not duplicate.'.format(lib.get_timestamp(),
                                                                                                  new_member_id))

    # Remove a member from the group view
    def remove_member(self, old_member):
        if self.members.__contains__(old_member):
            self.members.remove(old_member)
            print('>> {0}\t Member {1} left'.format(lib.get_timestamp(), old_member.name))
            logging.info('Member {0} left'.format(old_member.name))
        else:
            print('>> {0}\t Member {1} was not in the group view - did not attempt removal.'.format(lib.get_timestamp(),
                                                                                                    old_member.name))

    def contains(self, member):
        if self.members.__contains__(member):
            return True
        return False

    def get_difference(self, members_set=set()):
        return [item for item in self.members if item not in members_set]

    def get_members(self):
        return self.members

    def get_size(self):
        return len(self.members)

    def erase(self):
        self.members = []
