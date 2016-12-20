#!/bin/bash

# JCF, Dec-20-2016

# The following four lines should kick off all non-empty SDAQ_*.sh scripts in
# this package's bin/ directory

scriptdir=$( cd $(dirname $0) ; pwd -P )
basedir=$scriptdir/..
. $scriptdir/daqutils.sh
cd $basedir

state_true="0"
check_for_state "stopped" state_true

if [[ "$state_true" == "1" ]]; then
    echo "success"
else
    echo
    echo "DAQ does not appear to be in the \"stopped\" state, exiting..."
    exit 1
fi

$scriptdir/setdaqcomps.sh component01 component02

$scriptdir/send_transition.sh boot docs/config.txt

wait_until_no_longer booting

state_true="0"
check_for_state "booted" state_true

if [[ "$state_true" != "1" ]]; then
    echo "DAQ failed to enter booted state; exiting $0"
    exit 2
fi
