#!/bin/env bash

if [[ "$#" != "2" ]]; then
    echo "Usage: $0 <daq running time in seconds (0 if you want to run until ctrl-C is hit) > <run #>"
    exit 0
fi

starttime=$(date +%s)

daq_time_in_seconds=$1
runnum=$2

if ! [[ $daq_time_in_seconds =~ ^[0-9-]+$ ]]; then
    echo 'Entered value for daq running time of "'$daq_time_in_seconds'" does not appear to be an integer'
    exit 10
fi

if ! [[ $runnum =~ ^[0-9-]+$ ]]; then
    echo 'Entered value for run number of "'$daq_time_in_seconds'" does not appear to be an integer'
    exit 20
fi

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

    # Initialize the DAQ
    
    $scriptdir/sendcmd.sh init

    wait_until_no_longer initializing

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
    else
	echo "Will acquire data until Ctrl-C is hit"
	sleep 10000000000
    fi

    clean_shutdown
}

# clean_shutdown() will be called either (A) after the DAQ has run for
# the user-requested period of time, or (B) after ctrl-C has been hit
# (in which case it's called by the external_termination() handler
# function. It will issue a "stop" if it sees the DAQ is in the
# "running" state; either way, it issues a "terminate"

function clean_shutdown() {

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

    $scriptdir/sendcmd.sh terminate

    wait_until_no_longer terminating

    state_true="0"
    check_for_state "stopped" state_true

    if [[ "$state_true" != "1" ]]; then
	echo "DAQ unexpectedly not in stopped state;  exiting "$( basename $0)
	exit 90
    fi

    endtime=$(date +%s)
    runningtime=$(( $endtime - $starttime ))

    echo $(basename $0)" completed; script was up for $runningtime seconds"
    exit 0
}

function external_termination() {

    clean_shutdown
}


main $@





