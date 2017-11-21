#!/bin/env bash

. $ARTDAQ_DAQINTERFACE_DIR/bin/daqinterface_functions.sh

for port in "$@"; do

    daqinterface_pid=$( ps aux | grep -E "python.*daqinterface.py\s+--rpc-port\s+$port" | grep -v grep | awk '{print $2}' )
    tee_pid=$( ps aux | grep -E "tee.*DAQInterface_port${port}.log" | grep -v grep | awk '{print $2}' )

    if [[ -n $daqinterface_pid ]]; then
	echo "Killing DAQInterface listening on port $port"
    else
	echo "No DAQInterface listening on port $port was found" >&2
	continue
    fi

    kill $daqinterface_pid $tee_pid 
    
done

echo
echo "Remaining DAQInterface instances (if any): "
list_daqinterfaces
