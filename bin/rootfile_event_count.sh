#!/bin/env bash

if [[ $# != 1 ]]; then
    echo "Please pass run number as argument" >&2
    exit 10
fi

runnum=$1

recorddir=$( awk '/record_directory/ { print $2} ' .settings )
recorddir=$( echo $( eval echo $recorddir ) )  # Expand environ variables in string


if [[ ! -e $recorddir/$runnum ]]; then
    echo "Unable to find expected subdirectory \"$runnum\" in run record directory \"$recorddir\"" >&2
    exit 20
fi

# JCF, Jan-22-2017

# Big assumption: that the setup script lies in the parent directory
# of the products directory used by the bash scripts...even
# potentially on other hosts

proddir=$( cat $PWD/.settings | awk '/productsdir_for_bash_scripts/ { print $2 }' )
proddir=$( echo $( eval echo $proddir ) )  # Expand environ variables in string

setupscript=$( cat $PWD/.settings | awk '/daq_setup_script/ { print $2 }' )

cd $recorddir/$runnum

total_events=0

file_locations=""

for file in $recorddir/$runnum/Aggregator*.fcl ; do

    agg_host=$( echo $file | sed -r 's/.*Aggregator_(.*)_.*/\1/' )
    agg_dir=$( sed -r -n '/^\s*#/d;/fileName.*\.root/s/.*fileName.*(\/.*\/).*/\1/p' $file )
    if [[ -n $agg_dir && ! $file_locations =~ "${agg_host}:${agg_dir}" ]]; then
	file_locations="${agg_host}:${agg_dir} ${file_locations}"
    fi
done

for file_location in $file_locations ; do

    agg_host=$( echo $file_location | sed -r -n 's/(.*):.*/\1/p' )
    agg_dir=$( echo $file_location | sed -r -n 's/.*:(.*)/\1/p' )

    runnum_padded=$( printf "%06d" $runnum )

    cmd="tmpfile=/tmp/"$(uuidgen)".C ; echo '{TChain chain(\"Events\"); chain.Add(\""$agg_dir"/*_r"${runnum_padded}"_*.root\"); cout << chain.GetEntries() << endl;}' > \$tmpfile; cd "$proddir"/.. ; . "$setupscript"; root -q -b -l \$tmpfile ; rm -f \$tmpfile"

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

