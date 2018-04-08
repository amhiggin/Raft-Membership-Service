
class GroupAddressMessage:

    def __init__(self, group_id, group_address):
        self.__group_address = group_address
        self.__group_id = group_id

    def get_group_address(self):
        return self.__group_address

    def get_group_id(self):
        return self.__group_id
