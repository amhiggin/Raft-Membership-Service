'''
This is one of the servers in the RAFT (?) distributed system.
Each member has a group view, a mode (normal node/manager node), and a log of what operations it has performed.
To be decided: communication protocol (TCP/UDP), membership management protocol (RAFT/Paxos/etc), other recovery mechanisms, service to be provided.
'''

import thread, os, sys
from socket import *
import MessageType
import MemberLib as lib
import GroupView, Log

SERVER_PORT = 45678  # Review
ERROR_CODE = 0  # Default


class Member:

    def __init__(self):
        self.group_view = GroupView
        self.log = Log

        # Determined at runtime
        self.id = None
        self.server_socket = None
        self.heartbeat_window_timer = None

    def get_group_view(self):
        return self.group_view

    def new_response_thread(connection, client_address):
        lib.print_message('Received new connection from %s'.format(client_address))
        connected = True

        while connected:
            data_received = connection.recv(4096).decode()
            if not data_received:
                continue
                # keep connection alive
            else:
                lib.print_message("Received data: " + data_received)
                connected = lib.respond_to_message(connection, data_received)
        connection.close()

    def start_serving(self):
        global ERROR_CODE
        running = True

        while running:
            try:
                self.server_socket = socket(AF_INET, SOCK_STREAM)
                # server_socket = socket(AF_INET, SOCK_DGRAM) # If using UDP
                self.server_socket.bind((gethostbyname(getfqdn()), SERVER_PORT))
                self.server_socket.listen(5)
                lib.print_message('Server is ready to receive')
                while True:
                    try:
                        connection, client_address = self.server_socket.accept()
                        thread.start_new_thread(target=self.new_response_thread, args=(connection, client_address))
                    except Exception as e:
                        ERROR_CODE = 2
                        self.server_socket.close()
            except Exception as e1:
                lib.print_message(e1.message)
                ERROR_CODE = 1
            finally:
                sys.exit(ERROR_CODE)
