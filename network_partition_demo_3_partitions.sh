#!/bin/bash

# Create directory for writing logs to, if it does not already exist
mkdir -p MemberLogs;

echo "Launching $NUM_SERVERS nodes"

for i in $(seq 2 5)
do
        python3 "$(pwd)"/member/Member.py False 0 &
        #python3 member/Member.py False 0 &
done

for i in $(seq 6 7)
do
        python3 "$(pwd)"/member/Member.py False 45 '224.3.29.72' &
        #python3 member/Member.py False 45 '224.3.29.72' &
	echo "Partition node launched - minority partition 1"
done

for i in $(seq 8 9)
do
        python3 "$(pwd)"/member/Member.py False 45 '224.3.29.71' &
        #python3 member/Member.py False 45 '224.3.29.71' &
	echo "Partition node launched - minority partition 2"
done
python3 "$(pwd)"/member/Member.py True 0
#python3 member/Member.py True 0


