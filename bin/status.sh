#!/bin/env bash

scriptdir="$(dirname "$0")"
. $scriptdir/package_setup.sh xmlrpc_c

xmlrpc_retval=$?

if [[ "$xmlrpc_retval" != "0" ]]; then
    echo "Problem attempting to setup xmlrpc_c package" >&2
    exit 40
fi

. $DAQINTERFACE_DIR/bin/daqinterface_functions.sh
daqinterface_preamble

full_cmd="xmlrpc http://localhost:$DAQINTERFACE_PORT/RPC2 state daqint "
eval $full_cmd

exit 0
