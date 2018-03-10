'''
    This is a client which will connect to the distributed system for test purposes.
    To be decided: communication protocol, etc.
'''
import sys
sys.path.append("../")
import ClientLib as lib

DISPLAY_USER_OPTIONS = "---------\n>> {0} Client:\t".format(lib.get_timestamp()) + \
                       "Enter:\n\t- 1 to request the current group membership.\n\t- x to terminate."


def main():
    lib.print_message('Hello world from client')
    running = True

    while running:
        # Display user options until they decide to exit
        try:
            from pip._vendor.distlib.compat import raw_input
            user_input = raw_input(DISPLAY_USER_OPTIONS)
            if user_input == "1":
                response = lib.send_request()
            elif user_input == 'x':
                running = False
            else:
                lib.print_message("You said: " + user_input + ", which is invalid. Give it another go!\n")
        except Exception as e:
            lib.print_message('An error occurred during client operation: ' + e.message)

    lib.print_message("Terminating... Goodbye world!")
    exit(0)


if __name__ == "__main__":
    main()