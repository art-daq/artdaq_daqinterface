#!/bin/env bash

if [[ $# != 1 ]]; then
    echo "Please pass run number as argument" >&2
    exit 10
fi

. $DAQINTERFACE_BASEDIR/bin/package_setup.sh root

root_retval=$?

if [[ "$root_retval" != "0" ]]; then
    echo "Problem attempting to setup root package" >&2
    exit 40
fi

runnum=$1

recorddir=$( awk '/record_directory/ { print $2} ' $DAQINTERFACE_SETTINGS )
recorddir=$( echo $( eval echo $recorddir ) )  # Expand environ variables in string


if [[ ! -e $recorddir/$runnum ]]; then
    echo "Unable to find expected subdirectory \"$runnum\" in run record directory \"$recorddir\"" >&2
    exit 20
fi

cd $recorddir/$runnum

total_events=0

file_locations=""

for proctype in Aggregator DataLogger ; do
    for file in $( ls $recorddir/$runnum/${proctype}*.fcl 2>/dev/null ) ; do

	agg_host=$( echo $file | sed -r 's/.*'${proctype}'_(.*)_.*/\1/' )
	agg_dir=$( sed -r -n '/^\s*#/d;/fileName.*\.root/s/.*fileName[^/]*(\/.*\/).*/\1/p' $file )
	if [[ -n $agg_dir && ! $file_locations =~ "${agg_host}:${agg_dir}" ]]; then
	    file_locations="${agg_host}:${agg_dir} ${file_locations}"
	fi
    done
done

for file_location in $file_locations ; do

    agg_host=$( echo $file_location | sed -r -n 's/(.*):.*/\1/p' )
    agg_dir=$( echo $file_location | sed -r -n 's/.*:(.*)/\1/p' )

    runnum_padded=$( printf "%06d" $runnum )

    cmd="tmpfile=/tmp/"$(uuidgen)".C ; echo '{TChain chain(\"Events\"); chain.Add(\""$agg_dir"/*_r"${runnum_padded}"_*.root\"); cout << chain.GetEntries() << endl;}' > \$tmpfile;  root -q -b -l \$tmpfile 2>/dev/null; rm -f \$tmpfile"

    if [[ "$agg_host" != "localhost" && "$agg_host" != $HOSTNAME ]]; then
	nevents=$( ssh $agg_host "$cmd" | tail -1 )
    else
	nevents=$( eval "$cmd" | tail -1 )
    fi

    if [[ $nevents =~ ^[0-9]+$ ]]; then
	total_events=$(( total_events + nevents ))
    else
	echo "# of events produced by aggregator initialized by $file came out to be a noninteger: ${nevents}. Will skip remainder of test." >&2
	exit 30
    fi

done

echo $total_events

