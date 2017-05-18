#!/bin/env bash

badargs=false
cmd=$1

xmlrpc_arg=
translated_cmd=

scriptdir="$(dirname "$0")"
. $scriptdir/package_setup.sh xmlrpc_c

xmlrpc_retval=$?

if [[ "$xmlrpc_retval" != "0" ]]; then
    echo "Problem attempting to setup xmlrpc_c package" >&2
    exit 40
fi


case $cmd in
    "boot")
	test $# -gt 1 || badargs=true 
	translated_cmd="booting"
	daqinterface_config_file=$2
	xmlrpc_arg="daqinterface_config:s/"${daqinterface_config_file}
	;;
    "config")
	test $# == 2 || badargs=true 
	translated_cmd="configuring"
	xmlrpc_arg="config:s/"$2
	;;
    "start")
	test $# == 1 || badargs=true 
	translated_cmd="starting"

	run_records_dir=$( awk '/record_directory/ { print $2 }' .settings )
	run_records_dir=$( echo $( eval echo $run_records_dir ) )  # Expand environ variables in string
	
        highest_runnum=$( ls -1 $run_records_dir | sort -n | tail -1 )

	xmlrpc_arg="run_number:i/"$((highest_runnum + 1))
	;;
    "stop")
	test $# == 1 || badargs=true 
	translated_cmd="stopping"
	;;
    "shutdown")
	test $# == 1 || badargs=true 
	translated_cmd="shutting"
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
    full_cmd=${full_cmd}" 'struct/{ignored_variable:i/999}' "
fi

echo $full_cmd 
eval $full_cmd 
exit 0
