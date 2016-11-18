#!/bin/env bash

badargs=false
cmd=$1

runnum_token=""
config_token=",config:s/artdaqdemo"
translated_cmd=

case $cmd in
    "init")
	test $# == 1 || badargs=true 
	translated_cmd="initializing"
#	config_token=",config:s/"$2
	;;
    "start")
	test $# == 2 || badargs=true 
	translated_cmd="starting"
	runnum_token=",run_number:i/"$2
	;;
    "stop")
	test $# == 1 || badargs=true 
	translated_cmd="stopping"
	;;
    "terminate")
	test $# == 1 || badargs=true 
	translated_cmd="terminating"
	;;
    *)
	echo "Unknown command \"$cmd\" passed" >&2
	exit 30
	;;
esac

if [[ "$badargs" = true ]]; then
    echo "Incorrect arguments passed to $0" >&2
    exit 20
fi


full_cmd="xmlrpc http://localhost:5570/RPC2 state_change daqint "${translated_cmd}" 'struct/{daq_comp_list:struct/{component01:array/(s/pdunedaq01.fnal.gov,5305)}"${config_token}${runnum_token}"}'"

( cd ~/lbnedaq ; . setupLBNEARTDAQ 2>&1 > /dev/null; echo $full_cmd ; eval $full_cmd )

