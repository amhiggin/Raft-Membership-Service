#!/bin/sh

#
# Note: for options 1 and 2, the client requires that the address of the group
#       first be obtained by selecting option '3'.
#


PORT=${1:-8900};

# Launch a single client
echo "starting client on port $PORT"
python3 client/Client.py $PORT
