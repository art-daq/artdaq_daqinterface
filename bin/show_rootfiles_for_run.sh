#!/bin/bash


if [[ $# != 1 && $# != 2 ]] ; then
     echo "Usage: $0 <run number> (first N events -- default 0)"
     exit 1
fi

runnum=$1
nevents=0

if [[ -n $2 ]]; then
    nevents=$2
fi

. $ARTDAQ_DAQINTERFACE_DIR/bin/exit_if_bad_environment.sh
. $ARTDAQ_DAQINTERFACE_DIR/bin/diagnostic_tools.sh


if [[ "$runnum" =~ ^[0-9]+$ ]]; then
    echo "Run number is $runnum"
else
    echo "Error: run number \"$runnum\" isn't an integer; exiting..." >&2
    exit 1
fi

if [[ "$nevents" =~ ^[0-9]+$ ]]; then

    if (( $nevents > 0 )); then
	echo "Error: support for showing >0 events not yet implemented; exiting..." >&2
	exit 1
    fi

    echo "Will show the first $nevents events from the root file(s) (if any) produced in the run"
else
    echo "Error: number of events to display \"$nevents\" isn't an integer; exiting..." >&2
    exit 1
fi

if [[ ! -d $recorddir/$runnum ]]; then
    echo "Unable to find the expected run record directory \"$recorddir/$runnum\" associated with run $runnum; exiting..." >&2
    exit 1
fi

for file in $recorddir/$runnum/*.fcl ; do

proclabel=$( echo $file | sed -r "s!^.*/([^/]+)\.fcl.*!\1!" )

sedline='s/^\s*fileName\s*:\s*(\S+\.root)\s*/\1/p'

nmatches=$( sed -r -n $sedline $file | wc -l )

if (( $nmatches == 0 )); then
    continue
elif (( $nmatches == 1 )); then

    file_format=$( sed -r -n $sedline $file )
    #echo "Initial file format is $file_format"

    runnum_format=$( echo $file_format | sed -r 's/.*(%0[0-9])r.*/\1d/' )

    if [[ -n $runnum_format ]]; then
	runnum_token=$( printf $runnum_format $runnum )
	file_format=$( echo $file_format | sed -r 's/%0[0-9]r/'$runnum_token'/' )
    fi

    file_format=$( echo $file_format | sed -r 's/%[^_\.]+/\*/g' )
    file_format=$( echo $file_format | sed -r 's/"//g' )

    if [[ -e $recorddir/$runnum/ranks.txt ]]; then
	prochost=$( sed -r -n 's/^(\S+)\s+([0-9]+)\s+'$proclabel'.*/\1/p' $recorddir/$runnum/ranks.txt )
	
	if [[ -n $prochost ]]; then
	    echo ${prochost}:
	    if [[ "$prochost" != "$HOSTNAME" ]]; then
		ssh $prochost "ls -l $file_format" 
	    else
		ls -l $file_format
	    fi
	else
	    cat<<EOF >&2

Unable to determine host that artdaq process $proclabel from run
$runnum ran on based on examination of
$recorddir/$runnum/ranks.txt. Exiting...

EOF
		exit 1
	fi

    else
	echo "Unable to find expected artdaq process info file \"$recorddir/$runnum/ranks.txt\"; exiting..." >&2
	exit 1
    fi

elif (( $nmatches > 1 )); then
    echo "Error: found more than one potential root file listed in $file; exiting..." >&2
    sed -r -n $sedline $file >&2
    exit 1
fi

done



