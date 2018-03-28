'''
    This is a client which will connect to the distributed system for test purposes.
    To be decided: communication protocol, etc.
'''
import sys
import socket
from pip._vendor.distlib.compat import raw_input
sys.path.append("../")
import client.ClientLib as lib

DISPLAY_USER_OPTIONS = "---------\n>> {0} Client:\t".format(lib.get_timestamp()) + \
                       "Enter:\n\t- 1 to request the current group membership.\n\t- x to terminate."
TIMEOUT_PERIOD_SECONDS = 30


def main(socket_port):
    lib.print_message('Hello world from client')
    running = True
    self_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self_socket.bind(('', 12345))
    self_socket.settimeout(TIMEOUT_PERIOD_SECONDS)

    while running:
        # Display user options until they decide to exit
        try:
            user_input = raw_input(DISPLAY_USER_OPTIONS)
            if user_input == "1":
                group_view = lib.send_request(self_socket)
                if group_view is None:
                    lib.print_message("No response after {0} seconds".format(TIMEOUT_PERIOD_SECONDS))
                else:
                    lib.print_message("Group response: The group view is {0}".format(group_view))
            elif user_input == 'x':
                running = False
            else:
                lib.print_message("You said: " + user_input + ", which is invalid. Give it another go!\n")
        except Exception as e:
            lib.print_message('An error occurred during client operation: ' + str(e))

    lib.print_message("Terminating... Goodbye world!")
    exit(0)


if __name__ == "__main__":
    if sys.argv[0] is not None:
        main(sys.argv[0])
    else:
        lib.print_message("Required port number: none specified. Exiting.")