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

method=$( sed -r -n 's/^process management method: (\S+).*/\1/p' $metadata_file)

files=$( sed -n '/^process manager logfile/,/^\s*$/p' $RUNRECORDS/$runnum/metadata.txt | sed '1d;$d' )

if [[ "$method" == "pmt" && -n $files ]]; then

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
	    else
		echo "Ability to examine logfile on remote host (\"$logfile\") not yet implemented"
		exit 0
	    fi
	else
	    echo $file
	fi
    done

    exit 0

else


    
    cat>&2<<EOF

    Unable to find the process manager logfile for run $runnum; this
    is because according to the metadata file "$metadata_file" the 
    DAQINTERFACE_PROCESS_MANAGEMENT_METHOD environment
    variable was set to "$method" instead of "pmt" during that run

EOF

exit 1

fi





