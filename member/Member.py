'''
This is one of the servers in the RAFT (?) distributed system.
Each member has a group view, a mode (normal node/manager node), and a log of what operations it has performed.
To be decided: communication protocol (TCP/UDP), membership management protocol (RAFT/Paxos/etc), other recovery mechanisms, service to be provided.
'''

import thread

from flask import *
from flask_restful import *

import GroupView
import Log
import MemberLib as lib

ERROR_CODE = 0  # Default

app = Flask(__name__)
api = Api(app)


class Member(Resource):

    def __init__(self):
        self.id = lib.register_member()
        self.group_view = lib.request_group_view()
        self.log = lib.request_current_log()
        self.heartbeat_window_timer = None
        self.mode = 'Member' # Can have mode 'Monitor' mode if elected leader.

    def get_group_view(self):
        return self.group_view

    def get(self):
        # TODO
        pass

    def post(self):
        # TODO
        pass


api.add_resource(Member, '/')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)

