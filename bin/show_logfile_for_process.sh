#!/bin/bash


if (( $# != 2 && $# != 3)) ; then
     echo "Usage: $0 <run number> <process label> (examine)"
     exit 1
fi

runnum=$1
proclabel=$2
examine=$3

. $ARTDAQ_DAQINTERFACE_DIR/bin/diagnostic_tools.sh

metadata_file=$recorddir/$runnum/metadata.txt

if [[ ! -e $metadata_file ]]; then
    echo "Unable to find expected metadata file $metadatafile" >&2
    exit 1
fi

for procname in boardreader eventbuilder routingmaster aggregator; do

    logfiles=$( sed -r -n '/'$procname' logfiles:/,/^$/p' $metadata_file | sed '1d;$d')

    for logfile in $logfiles; do

	if [[ -n $( echo $logfile | sed -r -n '/'$proclabel'/p') ]]; then

	    host=$( echo $logfile | awk 'BEGIN{FS=":"}{print $1}' )
	    filename=$( echo $logfile | awk 'BEGIN{FS=":"}{print $2}' )

	    if [[ -n $examine && "$examine" != "0" ]]; then

		if [[ "$host" == "$HOSTNAME" || "$host" == "localhost" ]]; then
		    if [[ -e $filename ]]; then
			less $filename
			exit 0
		    else
			cat <<EOF

$metadata_file lists 
$filename
as being on this host but it doesn't appear to exist (any longer)

EOF
		    
		    fi
		else
		    echo "Ability to examine logfile on remote host (\"$logfile\") not yet implemented"
		    exit 0
		fi
	    else

		echo $logfile
		exit 0
	    fi
	fi
    done
done

echo "Unable to find logfile corresponding to process \"$proclabel\" from run $runnum" >&2
exit 1

