#!/bin/env bash

echo "JCF, Dec-7-2018: this script is deprecated until further notice"
exit 1

# JCF, Nov-27-2017

# Note that this only provides an accurate event count if the ONLY
# files matching the wildcard 
# "*<0-padded run number 6 characters wide>*_.root" come from the run 
# in question. This might not hold if, e.g., there are filenames with
# different prefixes, or if a run with the same # has been performed
# before

if [[ $# != 1 ]]; then
    echo "Please pass run number as argument" >&2
    exit 10
fi

runnum=$1

. $ARTDAQ_DAQINTERFACE_DIR/bin/package_setup.sh root

root_retval=$?

if [[ "$root_retval" != "0" ]]; then
    echo "Problem attempting to setup root package" >&2
    exit 40
fi

. $ARTDAQ_DAQINTERFACE_DIR/bin/diagnostic_tools.sh

if [[ ! -e $recorddir/$runnum ]]; then
    echo "Unable to find expected subdirectory \"$runnum\" in run record directory \"$recorddir\"" >&2
    exit 20
fi

cd $recorddir/$runnum

total_events=0

for file_location in $( file_locations ); do

    rootfile_host=$( echo $file_location | sed -r -n 's/(.*):.*/\1/p' )
    rootfile_dir=$( echo $file_location | sed -r -n 's/.*:(.*)/\1/p' )

    runnum_padded=$( printf "%06d" $runnum )

    cmd="tmpfile=/tmp/"$(uuidgen)".C ; echo '{TChain chain(\"Events\"); chain.Add(\""$rootfile_dir"/*"${runnum_padded}"*_*.root\"); cout << chain.GetEntries() << endl;}' > \$tmpfile;  root -q -b -l \$tmpfile 2>/dev/null; rm -f \$tmpfile"

    if [[ "$rootfile_host" != "localhost" && "$rootfile_host" != $HOSTNAME ]]; then
	nevents=$( ssh $rootfile_host "$cmd" | tail -1 )
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

