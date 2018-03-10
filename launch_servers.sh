#!/bin/bash

SERVER_STATE=$2
NUM_SERVERS=$1


if [ "$SERVER_STATE" = "leader" ] && [ $NUM_SERVERS -ge 1 ] ; then
	echo "Cannot start more than one leader at a time!"
	exit 1

fi
if [ "$SERVER_STATE" = "candidate" ] ; then
	echo "Cannot start a server in state candidate!"
	exit 2
fi

echo "Launching $NUM_SERVERS nodes"

for i in $( seq 2 $NUM_SERVERS )
do
        python3 "$(pwd)"/member/Member.py $SERVER_STATE &
done
python3 "$(pwd)"/member/Member.py $SERVER_STATE
