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

    # The "in run <runnum> has ended" is printed out by SharedMemoryEventManager in artdaq v3_00_02

    file=$( grep -l "in run $runnum has ended" $fileglob )

    if [[ -n $file ]]; then
	if [[ -n $examine && "$examine" != "0" ]]; then
	    less $file
	else
	    ls $file
	fi
	exit 0
    else
	echo "Unable to find \"in run <runnum> has ended\" token in ${fileglob}, but that may be because the run didn't end cleanly, rather than because it's not the correct logfile"
	exit 1
    fi
else
    echo "An assumption about the metadata file has been broken; please contact John Freeman at jcfree@fnal.gov about this" >&2
    exit 1
fi





