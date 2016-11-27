#!/bin/env bash

badargs=false
cmd=$1

xmlrpc_arg=
translated_cmd=

case $cmd in
    "boot")
	test $# -gt 1 || badargs=true 
	translated_cmd="booting"
	shift  # Get rid of the first argument, i.e., "boot"
	components=$@
	components_file=$( dirname $0 )"/../components.txt"

	if [[ ! -e $components_file ]]; then
	    echo "Unable to find file containing allowed components, \"$components_file\"" >&2
	    exit 10
	fi

	xmlrpc_arg="daq_comp_list:struct/{"

	for comp in $components; do

	    comp_line=$( grep $comp $components_file )

	    if [[ -n $comp_line ]]; then
		host=$( echo $comp_line | awk '{print $2}' )
		port=$( echo $comp_line | awk '{print $3}' )
		xmlrpc_arg=${xmlrpc_arg}${comp}":array/(s/"${host}","${port}")"
	    else
		echo "Unable to find listing for component \"$comp\" in $components_file" >&2
		exit 20
	    fi
	done
	xmlrpc_arg=${xmlrpc_arg}"}"
	;;
    "config")
	test $# == 2 || badargs=true 
	translated_cmd="configuring"
#	xmlrpc_arg=",run_number:i/"$2
	xmlrpc_arg="config:s/"$2
	;;
    "start")
	test $# == 2 || badargs=true 
	translated_cmd="starting"
	xmlrpc_arg="run_number:i/"$2
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


full_cmd="xmlrpc http://localhost:5570/RPC2 state_change daqint "${translated_cmd}

if [[ -n $xmlrpc_arg ]]; then
    full_cmd=${full_cmd}" 'struct/{"${xmlrpc_arg}"}'"
else
    full_cmd=${full_cmd}" 'struct/{ignored:i/999}' "
fi

( cd ~/artdaq-demo-base ; . setupARTDAQDEMO 2>&1 > /dev/null; echo $full_cmd ; eval $full_cmd )

