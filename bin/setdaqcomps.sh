#!/bin/env bash

if [[ "$#" == "0" ]]; then

    cat>&2<<EOF

        No arguments were supplied to this script: you need to provide
        a list of boardreaders. For allowed boardreader names, execute 
        "listdaqcomps.sh"

EOF
    exit 1
fi


components=$@

. $ARTDAQ_DAQINTERFACE_DIR/bin/daqinterface_functions.sh
daqinterface_preamble

scriptdir="$(dirname "$0")"
. $scriptdir/package_setup.sh xmlrpc_c

xmlrpc_retval=$?

if [[ "$xmlrpc_retval" != "0" ]]; then
    echo "Problem attempting to setup xmlrpc_c package" >&2
    exit 40
fi

components_file=$DAQINTERFACE_KNOWN_BOARDREADERS_LIST

if [[ ! -e $components_file ]]; then
    
    cat>&2<<EOF

    Unable to find file containing allowed components, "$components_file"

EOF

    exit 10
fi


num_components=$( echo $components | wc -w)
comp_cntr=0

for comp in $components; do

    comp_cntr=$((comp_cntr + 1))

    comp_line=$( grep $comp $components_file )

    if [[ -n $comp_line ]]; then
	host=$( echo $comp_line | awk '{print $2}' )
	port=$( echo $comp_line | awk '{print $3}' )
	subsystem=$( echo $comp_line | awk '{print $4}' )

	#defaults
	port=${port:-"-1"}
	subsystem=${subsystem:-"1"}

	xmlrpc_arg=${xmlrpc_arg}${comp}":array/(s/"${host}","${port}","${subsystem}")"
	test $comp_cntr != $num_components && xmlrpc_arg=${xmlrpc_arg}","
    else
	
	cat>&2<<EOF

	Unable to find listing for component "$comp" in
	$components_file; will not send component list to DAQInterface

EOF

	exit 20
    fi
done

xmlrpc http://localhost:$DAQINTERFACE_PORT/RPC2 setdaqcomps "struct/{$xmlrpc_arg}"

exit $?
