#!/bin/env bash

scriptdir="$(dirname "$0")"
. $scriptdir/xmlrpc_setup.sh

xmlrpc_retval=$?

if [[ "$xmlrpc_retval" != "0" ]]; then
    echo "Problem attempting to setup xmlrpc_c package" >&2
    exit 40
fi

full_cmd="xmlrpc http://localhost:5570/RPC2 state daqint "
eval $full_cmd

exit 0
