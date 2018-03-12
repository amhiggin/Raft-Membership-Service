
class Message:

    def __init__(self, term, message_type, member_id, data=''):
        self.__term = term
        self.__message_type = message_type
        self.__member_id = member_id
        self.__data = data

    def get_term(self):
        return self.__term

    def get_message_type(self):
        return self.__message_type

    def get_member_id(self):
        return self.__member_id

    def get_data(self):
        return self.__data
