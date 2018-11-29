#!/bin/env bash

if [[ "$#" != 2 && "$#" != 3 ]]; then
    echo "Usage: "$( basename $0 )" <existing run number> <seconds to run> [optional argument \"--nostrict\"]"
    exit 0
fi

runnum=$1
seconds_to_run=$2

nostrict=false

if [[ -n $3 && $3 =~ nostrict ]]; then
    nostrict=true
fi

if ! [[ "$runnum" =~ ^[0-9]+$ ]] ; then 
    echo "Run number argument \"$runnum\" does not appear to be an integer; exiting..." >&2
    exit 1
fi

if [[ -z $ARTDAQ_DAQINTERFACE_DIR ]]; then
    cat >&2 <<EOF 

The ARTDAQ_DAQINTERFACE_DIR environment variable isn't set; you
need to have set up the DAQInterface environment to run this
script. See the DAQInterface wiki for details,
https://cdcvs.fnal.gov/redmine/projects/artdaq-utilities/wiki/Artdaq-daqinterface

EOF

exit 1
    
fi

. $ARTDAQ_DAQINTERFACE_DIR/bin/diagnostic_tools.sh

if $nostrict ; then
    
    cat<<EOF

The "--nostrict" option has been requested; will ignore code
differences between run $runnum and the run about to be performed

EOF
fi

if [[ -d $recorddir ]]; then
    echo "Will look in record directory \"$recorddir\" for run $runnum"
else
    echo "Unable to find expected record directory \"$recorddir\", exiting..." >&2
    exit 1
fi

if [[ ! -d $recorddir/$runnum ]]; then
    echo "Unable to find subdirectory \"$runnum\" in $recorddir; exiting..." >&2
    exit 1
fi

daq_setup_script=$( sed -r -n 's/^\s*DAQ\s+setup\s+script\s*:\s*(\S+).*$/\1/p' $recorddir/$runnum/boot.txt )

if [[ ! -e $daq_setup_script ]]; then
    cat >&2 <<EOF 

Can't find DAQ setup script "$daq_setup_script" 
listed in boot file for run $runnum ($recorddir/$runnum/boot.txt);
exiting...

EOF
    exit 1
fi

if ! $nostrict ; then
    res=$( check_code_changes_since_run.sh $runnum )
    
    if [[ -n $res ]]; then
	
	check_code_changes_since_run.sh $runnum
	
	cat<<EOF 

Since the code in the installation area which was used for run $runnum
appears to have changed (details above), this attempt to repeat run
$runnum will not proceed. To override this refusal because the change
in code is irrelevant to your reasons for repeating run $runnum,
re-run the command with the --nostrict option added at the end. 

EOF

	exit 1
    fi
fi

config=$( sed -r -n 's/^Config name: ([^#]+).*/\1/p' $recorddir/$runnum/metadata.txt )
comps=$( awk '/^Component/ { printf("%s ", $NF); }' $recorddir/$runnum/metadata.txt )

cmd="just_do_it.sh $recorddir/$runnum/boot.txt $seconds_to_run --config \"$config\" --comps \"$comps\""
echo "Executing $cmd"
eval $cmd

exit 0
