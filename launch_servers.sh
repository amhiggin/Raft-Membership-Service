#!/bin/bash

NUM_SERVERS=$1

# Create directory for writing logs to, if it does not already exist
mkdir -p MemberLogs;

echo "Launching $NUM_SERVERS nodes"

for i in $( seq 2 $NUM_SERVERS )
do
        python3 "$(pwd)"/member/Member.py False 0 &
        #python3 member/Member.py False 0 &
done
python3 "$(pwd)"/member/Member.py True 0
#python3 member/Member.py True 0