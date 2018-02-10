#!/bin/bash

if [ $# != 1 ] ; then
     echo "Usage: $0 <run #>"
     echo
     exit 1
fi

runnum=$1

echo

. $ARTDAQ_DAQINTERFACE_DIR/bin/diagnostic_tools.sh

metadata_file=$recorddir/$runnum/metadata.txt

if [[ ! -e $metadata_file ]]; then
    echo "Unable to find expected metadata file $metadatafile" >&2
    exit 1
fi

run_start_time=$( sed -r -n "s/Start time:\s*(.*)/\1/p" $metadata_file )
run_stop_time=$( sed -r -n "s/Stop time:\s*(.*)/\1/p" $metadata_file )

if [[ -z $run_start_time ]]; then
    run_start_time="unknown"
fi

if [[ -z $run_stop_time ]]; then
    run_stop_time="unknown"
fi

disclaimer="Be aware that warnings/errors are shown for ALL runs which appear in run ${runnum}'s logfile. Run $runnum start time is $run_start_time, stop time is $run_stop_time"
echo
echo $disclaimer
echo

output=$( show_logfile_for_run.sh $runnum )

if [[ "$?" == "0" ]]; then
    sed -r -n '{/MSG-e/{N;p};/MSG-w/{N;/Use of services.user parameter set is deprecated/d;/Fast cloning deactivated/d;p}}' $output

    echo
    echo $disclaimer
    echo

else
    echo $output
    exit 1
fi

