'''
This is a client which will connect to the distributed system for test purposes.
To be decided: communication protocol, etc.
'''

import ClientLib as lib


def print_message(message):
    print('Client:\t' + message + '\n')


def main():
    print('Hello world from client')
    lib.send_request()


if __name__ == "__main__":
    main()