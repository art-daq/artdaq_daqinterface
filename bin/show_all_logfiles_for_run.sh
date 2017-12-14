#!/bin/bash


if [[ $# != 1 && $# != 2 ]] ; then
     echo "Usage: $0 <run number> (examine)"
     exit 1
fi

runnum=$1
examine=$2

. $ARTDAQ_DAQINTERFACE_DIR/bin/diagnostic_tools.sh

metadata_file=$recorddir/$runnum/metadata.txt

if [[ ! -e $metadata_file ]]; then
    echo "Unable to find expected metadata file $metadatafile" >&2
    exit 1
fi

fileglob=$( sed -r -n '/pmt logfile/s/.*:(.*)/\1/p' $metadata_file )

if [[ -n $fileglob ]]; then

    res=$( grep -l "Started run $runnum" $fileglob )

    if [[ -n $res ]]; then

	files_for_run=$( awk -v desired_run="$runnum" -f $ARTDAQ_DAQINTERFACE_DIR/bin/show_all_logfiles_for_run.awk $(ls -tr $fileglob) )
	echo $files_for_run | tr " " "\n"

	if [[ -n $examine ]]; then
	    for file in $files_for_run; do
		less $file
	    done
	fi

    else
	echo "Unable to find \"Started run\" token in any of ${fileglob}, but one of them may be what you want"
    fi
else
    echo "Unable to deduce PMT logfile for run $runnum ; see if any further info is available in /data/lbnedaq/run_records" >&2
    exit 1
fi





