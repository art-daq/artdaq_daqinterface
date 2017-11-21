#!/bin/env bash

components=$@

scriptdir="$(dirname "$0")"
. $scriptdir/package_setup.sh xmlrpc_c

xmlrpc_retval=$?

if [[ "$xmlrpc_retval" != "0" ]]; then
    echo "Problem attempting to setup xmlrpc_c package" >&2
    exit 40
fi

components_file=$DAQINTERFACE_KNOWN_BOARDREADERS_LIST

if [[ ! -e $components_file ]]; then
    echo "Unable to find file containing allowed components, \"$components_file\"" >&2
    exit 10
fi

. $ARTDAQ_DAQINTERFACE_DIR/bin/daqinterface_functions.sh
daqinterface_preamble

num_components=$( echo $components | wc -w)
comp_cntr=0

for comp in $components; do

    comp_cntr=$((comp_cntr + 1))

    comp_line=$( grep $comp $components_file )

    if [[ -n $comp_line ]]; then
	host=$( echo $comp_line | awk '{print $2}' )
	port=$( echo $comp_line | awk '{print $3}' )
	xmlrpc_arg=${xmlrpc_arg}${comp}":array/(s/"${host}","${port}")"

	test $comp_cntr != $num_components && xmlrpc_arg=${xmlrpc_arg}","
    else
	echo "Unable to find listing for component \"$comp\" in $components_file" >&2
	exit 20
    fi
done

xmlrpc http://localhost:$DAQINTERFACE_PORT/RPC2 setdaqcomps "struct/{$xmlrpc_arg}"

exit $?
