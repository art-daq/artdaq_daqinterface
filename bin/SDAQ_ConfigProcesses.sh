#!/bin/bash

# JCF, Dec-20-2016

# The following four lines should kick off all non-empty SDAQ_*.sh scripts in
# this package's bin/ directory

scriptdir=$( cd $(dirname $0) ; pwd -P )
basedir=$scriptdir/..
. $scriptdir/daqutils.sh
cd $basedir

$scriptdir/send_transition.sh config demo

wait_until_no_longer configuring

state_true="0"
check_for_state "ready" state_true

if [[ "$state_true" != "1" ]]; then
    echo "DAQ failed to enter ready state; exiting $0"
    exit 60
fi
