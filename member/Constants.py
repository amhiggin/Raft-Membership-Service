from member import State

'''  Server constants '''
SERVER_PORT = 45678  # Review
DEFAULT_STATE = State.State.follower
MULTICAST_ADDRESS = '224.3.29.71'     # 224.0.0.0 - 230.255.255.255 -> Addresses reserved for multicasting
MULTICAST_PORT = 45678
PARTITION_MULTICAST_PORT = 45679
PARTITION_MULTICAST_ADDRESS = '224.3.29.72'
CLIENT_LISTENING_PORT = 56789
CONSENSUS_PORT = 54321

''' Generic constants '''
RECV_BYTES = 2048#1024
SLEEP_TIMEOUT = 1
AGREED = "agreed"
REMOVED = "removed"
TIMED_OUT = 'timed out'
SUCCESS = "success"
