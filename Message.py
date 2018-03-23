
class Message:

    def __init__(self, term, message_type, message_subtype, member_id, data=None):
        self.__term = term
        self.__message_type = message_type
        self.__message_subtype = message_subtype
        self.__member_id = member_id
        self.__data = data

    def __init__(self, term, message_type, message_subtype, member_id, data=None, index_of_latest_uncommitted_log=None, index_of_latest_committed_log=None, group_view=None):
        self.__term = term
        self.__message_type = message_type
        self.__message_subtype = message_subtype
        self.__member_id = member_id
        self.__index_of_latest_uncommitted_log = index_of_latest_uncommitted_log
        self.__index_of_latest_committed_log = index_of_latest_committed_log
        self.__group_view = group_view
        self.__data = data

    def get_term(self):
        return self.__term

    def get_message_type(self):
        return self.__message_type

    def get_message_subtype(self):
        return self.__message_subtype

    def get_member_id(self):
        return self.__member_id

    def get_index_of_latest_uncommited_log(self):
        return self.__index_of_latest_uncommitted_log

    def get_index_of_latest_commited_log(self):
        return self.__index_of_latest_committed_log

    def get_group_view(self):
        return self.__group_view

    def get_data(self):
        return self.__data
