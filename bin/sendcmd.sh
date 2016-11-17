#!/bin/env bash

if [[ ($1 != "start" && $# != 1 ) || ( $1 == "start" && $# != 2 ) ]]; then
    echo "Wrong arguments" >&2
    exit 10
fi

cmd=$1
runnum=$2

if ! [[ "$runnum" =~ "" || "$runnum" =~ ^[0-9]+$ ]]; then
    echo "Argument for run number is malformed"
    exit 20
fi

runnum_token=""
translated_cmd=

case $cmd in
    "init")
	translated_cmd="initializing"
	;;
    "start")
	translated_cmd="starting"
	runnum_token=",run_number:i/"$runnum
	;;
    "stop")
	translated_cmd="stopping"
	;;
    "terminate")
	translated_cmd="terminating"
	;;
    *)
	echo "Unknown command \"$cmd\" passed" >&2
	exit 30
	;;
esac

full_cmd="xmlrpc http://localhost:5570/RPC2 state_change daqint "${translated_cmd}" 'struct/{config:s/demo"${runnum_token}",daq_comp_list:struct/{component01:array/(s/pdunedaq01.fnal.gov,5305)}}'"

( cd ~/lbnedaq ; . setupLBNEARTDAQ 2>&1 > /dev/null; echo $full_cmd ; eval $full_cmd )

