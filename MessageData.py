class MessageData:

    def __init__(self, data_type, data=None):
        self.__data_type = data_type
        self.__data = data

    def get_data_type(self):
        return self.__data_type

    def get_data(self):
        return self.__data
