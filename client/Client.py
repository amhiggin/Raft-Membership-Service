'''
    This is a client which will connect to the distributed system for test purposes.
    To be decided: communication protocol, etc.
'''
import sys
sys.path.append("../")
import socket
import client.ClientLib as lib
from pip._vendor.distlib.compat import raw_input

DISPLAY_USER_OPTIONS = "---------\n>> {0} Client:\t".format(lib.get_timestamp()) + \
                       "Enter:\n\t- 1 to request the current group membership.\n\t- x to terminate.\n"
TIMEOUT_PERIOD_SECONDS = 30


def main(socket_port):
    self_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self_socket.bind(('', socket_port))
    self_socket.settimeout(TIMEOUT_PERIOD_SECONDS)
    running = True
    lib.print_message('Hello world from client, listening on port {0}'.format(socket_port))

    try:
        while running:
            user_input = raw_input(DISPLAY_USER_OPTIONS)
            if user_input == "1":
                group_view = lib.send_request(self_socket)
                if group_view is None:
                    lib.print_message("The request timed out. There may have been an issue. Try again!")
                else:
                    lib.print_message("Group response: The group view is {0}".format(group_view))
            elif user_input == 'x':
                running = False
            else:
                lib.print_message("You said {0}, which is an invalid option. Try again!".format(user_input))
    except Exception as e1:
        lib.print_message('An error occurred during client operation: ' + str(e1))
    finally:
        lib.print_message("Exiting - Goodbye world!")
        exit(1)


if __name__ == "__main__":
    try:
        if sys.argv[1] is not None:
            main(int(sys.argv[1]))
        else:
            lib.print_message("Usage: <port_num>")
    except Exception as e:
        lib.print_message("An exception occurred in main method: {0}".format(str(e)))
