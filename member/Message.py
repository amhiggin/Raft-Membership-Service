import MessageType


class Message:

    def __init__(self, term, message_type, data=''):
        self.__term = term
        self.__message_type = message_type,
        self.__data = data

    def get_term(self):
        return self.__term

    def get_message_type(self):
        return self.__message_type

    def get_data(self):
        return self.__data

    def get_string_representation(self):
        # TODO discuss format and implement
        pass
