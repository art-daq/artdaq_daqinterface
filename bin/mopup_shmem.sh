#!/bin/env bash

if (( "$#" != 1 && "$#" != 2)) || [[ "$#" == 2 && "$2" != "--force" ]]; then
    echo "Usage: "$( basename $0 )" <partition number to mopup> (optional \"--force\")"
    exit 1
fi

retval=0 #Innocent until proven guilty
partition=$1

force_cleanup=false
if [[ -n $2 ]]; then
    force_cleanup=true
fi

if ! [[ "$partition" =~ [0-9]+ ]]; then
    echo "Partition number needs to be an integer; exiting..." >&2
    exit 1
fi

. $ARTDAQ_DAQINTERFACE_DIR/bin/exit_if_bad_environment.sh
. $ARTDAQ_DAQINTERFACE_DIR/bin/daqutils.sh

if ! $force_cleanup; then

if [[ -n $( listdaqinterfaces.sh | grep -E "\s+[Pp]artition\s+$partition\s+" ) ]]; then

    timeoutsecs=10

    cat<<EOF

A DAQInterface on partition $partition has been found; will confirm
that it's in the "stopped" state via a status.sh call with a
$timeoutsecs second timeout...

EOF

    res=$( timeout $timeoutsecs $ARTDAQ_DAQINTERFACE_DIR/bin/status.sh | tail -1 | tr "'" " " | awk '{print $2}' )
    
    if [[ "$res" == "stopped" ]]; then

    echo "DAQInterface in \"stopped\" state; will proceed with cleaning up the shared memory blocks"
    
    elif [[ "$res" == "" ]]; then

	cat <<EOF >&2

No state discovered after calling status.sh, this may be because the
$timeoutsecs second timeout was activated due to a communication
issue. If you want this script to clean up the shared memory blocks
regardless, execute it again with the option "--force"
added. Exiting...

EOF
	
      exit 1

    elif [[ "$res" != "stopped" ]]; then
	cat<<EOF >&2

After executing status.sh the DAQInterface instance on partition
$partition didn't confirm it's in the "stopped" state (result was
"$res"). If you want this script to clean up the shared memory blocks
regardless, execute it again with the option "--force"
added. Exiting...

EOF
	exit 1
    fi
fi

fi

token=$(( partition + 1))
hextoken=$( printf "%02x" $token )
#echo "Assuming that partition $partition appears as \"$hextoken\" in the shmem keys..."

num_blocks=$( ipcs | grep -E "^0xee${hextoken}|^0xbb${hextoken}|^0x${hextoken}00" | wc -l )
num_owned_blocks_before=$( ipcs | grep -E "^0xee${hextoken}|^0xbb${hextoken}|^0x${hextoken}00" | grep $USER | wc -l )

if (( $num_blocks != $num_owned_blocks_before )); then
    
    cat<<EOF >&2

WARNING: it appears that only $num_owned_blocks_before of $num_blocks shared
memory blocks associated with partition $partition are actually owned
by the user (\$USER == "$USER"); cleanup will be incomplete...

EOF
    retval=10
fi

for shmid in $( ipcs | grep -E "^0xee${hextoken}|^0xbb${hextoken}|^0x${hextoken}00" | grep $USER | awk '{print $2}' ); do
ipcrm -m $shmid
done

num_owned_blocks_after=$( ipcs | grep -E "^0xee${hextoken}|^0xbb${hextoken}|^0x${hextoken}00" | grep $USER | wc -l )

if (( $num_owned_blocks_after != 0 )); then
    retval=11
fi

echo $((num_owned_blocks_before - num_owned_blocks_after))" of $num_owned_blocks_before original shared memory blocks have been cleaned up (all of them should have been cleaned up)"

exit $retval

