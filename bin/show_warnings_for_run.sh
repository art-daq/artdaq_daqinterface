#!/bin/bash

if [ $# != 1 ] ; then
     echo "Usage: $0 <run #>"
     echo
     exit 1
fi

run=$1

echo

. $PWD/bin/get_daq_environment.sh

metadata_filename=$recorddir/$run/metadata.txt

if [[  -e $metadata_filename ]]; then

    fileglob=$( sed -r -n '/pmt logfile/s/.*:(.*)/\1/p' $metadata_filename )

    if [[ -n $fileglob ]]; then
		
	files_time_ordered=$( ls -tr $fileglob)

	tmplog=/tmp/$(uuidgen)

	cat $files_time_ordered > $tmplog

	res=$(grep "Started run $run" $tmplog)
	
	if [[ -z $res ]]; then
	    echo "Unable to find run listed in $fileglob" >&2
	    rm -f $tmplog
	    exit 1
	fi

	sed -r -n '/Started run '$run'/,/Started run '$((run+1))'/{/MSG-e/{N;p};/MSG-w/{N;/Use of services.user parameter set is deprecated/d;/Fast cloning deactivated/d;p}}' $tmplog

	rm -f $tmplog
    else
	echo "Unable to find pmt logfiles in $metadata_filename" >&2
    fi
else
    echo "Unable to find metadata file $metadata_filename" >&2
fi

echo
