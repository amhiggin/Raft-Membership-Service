'''
    This is a client which will connect to the distributed system for test purposes.
    To be decided: communication protocol, etc.
'''
import sys

sys.path.append(".")
sys.path.append("../")

import client.ClientLib as lib
# from pip._vendor.distlib.compat import raw_input

WELCOME_MESSAGE = 'Hello world from client, listening on port {0}'
DISPLAY_USER_OPTIONS = "---------\n>> {0} Client:\tEnter:\n\t- 1 to request the current group membership, given its address.\n\t- 2 to delete a group, given its address\n\t- 3 to see all available groups.\n\t- x to terminate.\n".format(lib.get_timestamp())
DISPLAY_REQUEST_FOR_GROUP_ADDRESS = "Enter the name of the group:\n"
REQUEST_TIMED_OUT = "The request timed out. There may have been an issue. Try again!"
USAGE_MESSAGE = "Usage: <port_num>"
EXIT_MESSAGE = "Exiting - Goodbye world!"
TRY_AGAIN_ = "You said {0}, which is an invalid option. Try again!"


def main(socket_port):
    self_socket = lib.setup_up_socket(socket_port)
    group_multicast_socket = lib.get_group_listener_socket()
    running = True
    lib.print_message(WELCOME_MESSAGE.format(socket_port))

    try:
        while running:
            user_input = input(DISPLAY_USER_OPTIONS)
            if user_input == "1":
                group_address = input(DISPLAY_REQUEST_FOR_GROUP_ADDRESS)
                group_view = lib.send_service_request(self_socket, group_address)
                if group_view is None:
                    lib.print_message(REQUEST_TIMED_OUT)
                else:
                    lib.print_message("Group response: The group view is {0}".format(group_view))
            elif user_input == "2":
                group_address = input(DISPLAY_REQUEST_FOR_GROUP_ADDRESS)
                deletion_response = lib.send_delete_request(self_socket, group_address)
                if deletion_response is None:
                    lib.print_message(REQUEST_TIMED_OUT)
                else:
                    lib.print_message("Deletion response: {0}".format(deletion_response))
            elif user_input == '3':
                '''show all groups in this block'''
                groups = lib.listen_for_groups(group_multicast_socket)
                if groups:
                    lib.print_message("All active groups are: " + str(groups))
                else:
                    lib.print_message("No active groups found")
            elif user_input == 'x':
                running = False
            else:
                lib.print_message(TRY_AGAIN_.format(user_input))
    except Exception as e1:
        lib.print_message('An error occurred during client operation: ' + str(e1))
    finally:
        lib.print_message(EXIT_MESSAGE)
        exit(1)


if __name__ == "__main__":
    try:
        if sys.argv[1] is not None:
            main(int(sys.argv[1]))
        else:
            lib.print_message(USAGE_MESSAGE)
    except Exception as e:
        lib.print_message("An exception occurred in main method: {0}".format(str(e)))
