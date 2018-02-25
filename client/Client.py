'''
This is a client which will connect to the distributed system for test purposes.
To be decided: communication protocol, etc.
'''
import ClientLib as lib


def main():
    lib.print_message('Hello world from client')
    while True:
        try:
            lib.send_request()
        except Exception as e:
            lib.print_message(e.message)
            exit(1)

if __name__ == "__main__":
    main()