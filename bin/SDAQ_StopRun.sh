#!/bin/bash

# JCF, Dec-20-2016

# The following four lines should kick off all non-empty SDAQ_*.sh scripts in
# this package's bin/ directory

scriptdir=$( cd $(dirname $0) ; pwd -P )
basedir=$scriptdir/..
. $scriptdir/daqutils.sh
cd $basedir

# Stop the DAQ, if necessary
    
state_true="0"
check_for_state "running" state_true

if [[ "$state_true" == "1" ]]; then
	
    $scriptdir/send_transition.sh stop
    wait_until_no_longer stopping
fi

sleep 1

state_true="0"
check_for_state "ready" state_true

if [[ "$state_true" != "1" ]]; then
    echo "DAQ unexpectedly not in ready state; exiting "$( basename $0)
    exit 80
fi

