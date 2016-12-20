#!/bin/bash

# JCF, Dec-20-2016

# The following four lines should kick off all non-empty SDAQ_*.sh scripts in
# this package's bin/ directory

scriptdir=$( cd $(dirname $0) ; pwd -P )
basedir=$scriptdir/..
. $scriptdir/daqutils.sh
cd $basedir

run_records_dir=$( awk '/record_directory/ { print $2 }' $basedir/.settings )
lastrun=$(ls -tr1 $run_records_dir | tail -1)
runnum=$(( lastrun + 1 ))

$scriptdir/send_transition.sh start $runnum

wait_until_no_longer starting

state_true="0"
check_for_state "running" state_true

if [[ "$state_true" != "1" ]]; then
    echo "DAQ failed to enter running state; exiting $0"
    exit 70
fi


