#!/bin/env bash

if [[ "$#" != "1" ]]; then
    echo "Usage: $0 <daq running time in seconds (0 if you want to run until ctrl-C is hit) > "
    exit 0
fi

config="demo"

starttime=$(date +%s)

daq_time_in_seconds=$1
runnum=$2

root_output_dir="/tmp"
run_records_dir=$HOME/run_records

if ! [[ $daq_time_in_seconds =~ ^[0-9-]+$ ]]; then
    echo 'Entered value for daq running time of "'$daq_time_in_seconds'" does not appear to be an integer'
    exit 10
fi

lastrun=$(ls -tr1 $run_records_dir | tail -1)
runnum=$(( lastrun + 1 ))

# See below for definition of "clean_shutdown" function

trap "clean_shutdown" SIGHUP SIGINT SIGTERM

scriptdir="$(dirname "$0")"

daqutils_script=$scriptdir/daqutils.sh

if ! [[ -e $daqutils_script ]]; then 
     echo $(date) "Unable to source $daqutils_script - script not found" >&2
     exit 30
else   
     . $daqutils_script
fi   


# And now define the main body of code (this function is not actually
# called until the very bottom of the script, in order to be able to
# use functions in the body of the main() function that aren't defined
# until lower in the script)

function main() {

    res=$( ps aux | grep -E "python.*daqinterface.py" | grep -v grep )

    if [[ -z $res ]]; then
	echo 
	echo "DAQInterface does not appear to be running, will exit.." >&2
	exit 40
    fi

    echo -n "Checking that the DAQ is in the \"stopped\" state..."

    state_true="0"
    check_for_state "stopped" state_true

    if [[ "$state_true" == "1" ]]; then
	echo "success"
    else
	echo
	echo "DAQ does not appear to be in the \"stopped\" state, exiting..."
	exit 50
    fi

    $scriptdir/sendcmd.sh boot $(dirname $0)/../docs/config_john.txt component01 component02

    wait_until_no_longer booting

    state_true="0"
    check_for_state "booted" state_true

    if [[ "$state_true" != "1" ]]; then
	echo "DAQ failed to enter booted state; exiting $0"
	exit 51
    fi

    # Initialize the DAQ
    
    $scriptdir/sendcmd.sh config $config

    wait_until_no_longer configuring

    state_true="0"
    check_for_state "ready" state_true

    if [[ "$state_true" != "1" ]]; then
	echo "DAQ failed to enter ready state; exiting $0"
	exit 60
    fi

    # Start the DAQ, and run it for the requested amount of time

    $scriptdir/sendcmd.sh start $runnum

    wait_until_no_longer starting

    state_true="0"
    check_for_state "running" state_true

    if [[ "$state_true" != "1" ]]; then
	echo "DAQ failed to enter running state; exiting $0"
	exit 70
    fi

    
    if [[ $daq_time_in_seconds > 0 ]]; then
	echo "Will acquire data for $daq_time_in_seconds seconds"
	sleep $daq_time_in_seconds
	clean_shutdown
    else
	echo "Will acquire data until Ctrl-C is hit"
	sleep 10000000000
    fi
}

# clean_shutdown() will be called either (A) after the DAQ has run for
# the user-requested period of time, or (B) after ctrl-C has been hit
# (in which case it's called by the external_termination() handler
# function. It will issue a "stop" if it sees the DAQ is in the
# "running" state; either way, it issues a "terminate"

function clean_shutdown() {

    echo "Entered clean_shutdown"

    # Stop the DAQ, if necessary
    
    state_true="0"
    check_for_state "running" state_true

    if [[ "$state_true" == "1" ]]; then
	
	$scriptdir/sendcmd.sh stop
	wait_until_no_longer stopping
    fi

    sleep 1

    state_true="0"
    check_for_state "ready" state_true

    if [[ "$state_true" != "1" ]]; then
	echo "DAQ unexpectedly not in ready state; exiting "$( basename $0)
	exit 80
    fi

    # And terminate it

    if false; then

	$scriptdir/sendcmd.sh terminate

	wait_until_no_longer terminating

	state_true="0"
	check_for_state "stopped" state_true

	if [[ "$state_true" != "1" ]]; then
	    echo "DAQ unexpectedly not in stopped state;  exiting "$( basename $0)
	    exit 90
	fi
    else
	echo "Skipping the terminate step"
    fi

    endtime=$(date +%s)
    runningtime=$(( $endtime - $starttime ))

    echo $(basename $0)" completed; script was up for $runningtime seconds"
}

function check_output_file() {

    local runtoken=$( awk 'BEGIN{ printf("r%06d", '$runnum')}' )
    
    local glob=$root_output_dir/*${runtoken}*.root
    local output_file=$( ls -tr1 $glob | tail -1 )    

    if [[ -n $output_file ]]; then
	ls -l $output_file
	return
    else
	echo "No file in $root_output_dir matches glob $glob" >&2
	exit 100
    fi
}

function check_run_records() {

    if [[ ! -d $run_records_dir/$runnum ]]; then
	echo "Unable to find expected run records subdirectory $run_records_dir/$runnum" >&2
	exit 200
    fi

    echo "Contents of $run_records_dir/$runnum :"
    ls -ltr $run_records_dir/$runnum 
}

main $@

echo
check_output_file
echo
check_run_records

exit 0
