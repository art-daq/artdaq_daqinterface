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

	# shift
	# shift
	# components=$@
	# components_file=$( dirname $0 )"/../components.txt"

	# if [[ ! -e $components_file ]]; then
	#     echo "Unable to find file containing allowed components, \"$components_file\"" >&2
	#     exit 10
	# fi

	# xmlrpc_arg=${xmlrpc_arg}",daq_comp_list:struct/{"

	# num_components=$( echo $components | wc -w)
	# comp_cntr=0

	# for comp in $components; do

	#     comp_cntr=$((comp_cntr + 1))

	#     comp_line=$( grep $comp $components_file )

	#     if [[ -n $comp_line ]]; then
	# 	host=$( echo $comp_line | awk '{print $2}' )
	# 	port=$( echo $comp_line | awk '{print $3}' )
	# 	xmlrpc_arg=${xmlrpc_arg}${comp}":array/(s/"${host}","${port}")"

	# 	test $comp_cntr != $num_components && xmlrpc_arg=${xmlrpc_arg}","
	#     else
	# 	echo "Unable to find listing for component \"$comp\" in $components_file" >&2
	# 	exit 20
	#     fi
	# done

	# xmlrpc_arg=${xmlrpc_arg}"}"
	;;
    "config")
	test $# == 2 || badargs=true 
	translated_cmd="configuring"
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
