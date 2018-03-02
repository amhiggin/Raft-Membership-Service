#!/bin/bash

NUM_SERVERS=$1

echo "Launching $NUM_SERVERS nodes"

for i in $( seq 2 $1 )
do
        python member/Member.py &
done
python member/Member.py 
