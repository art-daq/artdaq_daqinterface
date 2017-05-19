#!/bin/env bash

scriptdir="$(dirname "$0")"
. $scriptdir/package_setup.sh xmlrpc_c

xmlrpc_retval=$?

if [[ "$xmlrpc_retval" != "0" ]]; then
    echo "Problem attempting to setup xmlrpc_c package" >&2
    exit 40
fi

xmlrpc http://localhost:5570/RPC2 listconfigs
exit $?
