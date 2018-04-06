#!/bin/bash

# Create directory for writing logs to, if it does not already exist
mkdir -p MemberLogs;

echo "Launching new leader node"

python3 "$(pwd)"/member/Member.py True 0
#python3 member/Member.py True 0