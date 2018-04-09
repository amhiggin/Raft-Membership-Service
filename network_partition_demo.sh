#!/bin/bash

# Create directory for writing logs to, if it does not already exist
mkdir -p MemberLogs;

echo "Launching $NUM_SERVERS nodes"

for i in $( seq 2 5 )
do
        python3 "$(pwd)"/member/Member.py False 0 &
done

for i in $( seq 6 8)
do
        python3 "$(pwd)"/member/Member.py False 15 &
	echo "Partition node launched"
done
python3 "$(pwd)"/member/Member.py True 0
python3 member/Member.py True 0

