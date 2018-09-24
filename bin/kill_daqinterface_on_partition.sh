#!/bin/env bash

. $ARTDAQ_DAQINTERFACE_DIR/bin/daqinterface_functions.sh

for partition in "$@"; do

    daqinterface_pid=$( ps aux | grep -E "python.*daqinterface.py.*--partition-number\s+$partition" | grep -v grep | awk '{print $2}' )
    tee_pid=$( ps aux | grep -E "tee.*DAQInterface_partition${partition}.log" | grep -v grep | awk '{print $2}' )

    if [[ -n $daqinterface_pid ]]; then
	echo "Killing DAQInterface listening on partition $partition"
    else
	echo "No DAQInterface listening on partition $partition was found" >&2
	continue
    fi

    kill $daqinterface_pid $tee_pid 
    
done

echo
echo "Remaining DAQInterface instances (if any): "
list_daqinterfaces
