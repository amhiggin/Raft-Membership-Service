#!/bin/bash

NUM_SERVERS=$1

echo "Launching $NUMSERVERS servers"

for i in $( seq 2 $1 )
do
        python member/Member.py &
done
python member/Member.py 
