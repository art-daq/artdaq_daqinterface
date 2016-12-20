#!/bin/bash

# JCF, Dec-20-2016

# The following four lines should kick off all non-empty SDAQ_*.sh scripts in
# this package's bin/ directory

scriptdir=$( cd $(dirname $0) ; pwd -P )
basedir=$scriptdir/..
. $scriptdir/daqutils.sh
cd $basedir

$scriptdir/send_transition.sh terminate

wait_until_no_longer terminating

state_true="0"
check_for_state "stopped" state_true

if [[ "$state_true" != "1" ]]; then
    echo "DAQ unexpectedly not in stopped state;  exiting "$( basename $0)
    exit 90
fi

