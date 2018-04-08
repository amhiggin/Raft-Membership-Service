#!/bin/sh

PORT=${1:-8900};

# Launch a single client
echo "starting client on port $PORT"
python3 client/Client.py $PORT
