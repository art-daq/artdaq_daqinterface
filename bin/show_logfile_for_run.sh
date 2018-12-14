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

files=$( sed -n '/^process manager logfile/,/^\s*$/p' $RUNRECORDS/$runnum/metadata.txt | sed '1d;$d' )

if [[ -n $files ]]; then

    for file in $files; do

	host=$( echo $file | awk 'BEGIN{FS=":"}{print $1}' )
	filename=$( echo $file | awk 'BEGIN{FS=":"}{print $2}' )

	if [[ -n $examine && "$examine" != "0" ]]; then

	    if [[ "$host" == "$HOSTNAME" || "$host" == "localhost" ]]; then
		if [[ -e $filename ]]; then
		    less $filename
		else
		    cat <<EOF

$metadata_file lists 
$filename 
as being on this host but it doesn't appear to exist (any longer)

EOF
		    
		fi
	    fi
	else
	    echo $file
	fi
    done

    exit 0

else
    cat>&2<<EOF

    Unable to find the process manager logfile for run $runnum; this
    may be because the DAQINTERFACE_PROCESS_MANAGEMENT_METHOD
    environment variable was set to a choice other than "pmt" during
    that run

EOF

fi





