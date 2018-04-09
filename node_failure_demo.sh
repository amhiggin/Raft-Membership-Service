#!/usr/bin/env bash

# Create directory for writing logs to, if it does not already exist
mkdir -p MemberLogs;

python3 "$(pwd)"/member/Member.py False 0 0 0 &
python3 "$(pwd)"/member/Member.py False 0 0 0 &

python3 "$(pwd)"/member/Member.py False 0 20 20 &
echo "Node will fail for 20 seconds after waiting 20 seconds" &

python3 member/Member.py True 0


