#!/bin/env bash

if [[ "$#" == "0" ]]; then

    cat>&2<<EOF

        No arguments were supplied to this script: you need to provide
        a list of integers corresponding to the partitions of the
        DAQInterface instances you want killed. To see what
        DAQInterface instances are up, execute "listdaqinterfaces.sh"

EOF
    exit 1
fi

. $ARTDAQ_DAQINTERFACE_DIR/bin/daqinterface_functions.sh

scriptdir="$(dirname "$0")"
daqutils_script=$scriptdir/daqutils.sh

if ! [[ -e $daqutils_script ]]; then 
     echo $(date) "Unable to source $daqutils_script - script not found" >&2
     exit 30
else   
     . $daqutils_script
fi   

for partition in "$@"; do

    daqinterface_pid=$( ps aux | grep -E "python.*daqinterface.py.*--partition-number\s+$partition" | grep -v grep | awk '{print $2}' )
    tee_pid=$( ps aux | grep -E "tee.*DAQInterface_partition${partition}.log" | grep -v grep | awk '{print $2}' )

    if [[ -n $daqinterface_pid ]]; then
	
	export DAQINTERFACE_PARTITION_NUMBER=$partition
	state_true="0"
	check_for_state "stopped" state_true >&2 > /dev/null

	if [[ "$state_true" != "1" ]]; then
	    cat <<EOF

DAQInterface instance on partition $partition does not appear to be in
the "stopped" state:

EOF
	    status.sh | grep "Result\|String"

	    cat<<EOF 

Are you *sure* you want to go ahead and kill it? Doing so may result
in improper cleanup of artdaq processes, etc. Respond with "y" or "Y"
to kill; any other string entered will not kill the instance:

EOF

	    read response

	    if ! [[ "$response" =~ ^[yY]$ ]]; then
		echo "Will skip the killing of DAQInterface instance on partition $partition"
		continue
	    fi
	fi

	echo "Killing DAQInterface listening on partition $partition"
	kill $daqinterface_pid $tee_pid 

    else
	echo "No DAQInterface listening on partition $partition was found" >&2
	continue
    fi
    
done

echo
echo "Remaining DAQInterface instances (if any): "
list_daqinterfaces


