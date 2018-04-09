#!/usr/bin/env bash

# Create directory for writing logs to, if it does not already exist
mkdir -p MemberLogs;

#echo "Launching $NUM_SERVERS nodes"

#WAIT_TIME = ${1:-10};
#SLEEP_TIME = ${2:-10};

for i in $( seq 2 5 )
do
        python3 "$(pwd)"/member/Member.py False 0 0 0 &
done

for i in $( seq 6 8)
do
        python3 "$(pwd)"/member/Member.py False 0 10 10 &
	echo "Node will fail for $2 seconds after waiting $1 seconds"
done
# python3 "$(pwd)"/member/Member.py True 0
python3 member/Member.py True 0


