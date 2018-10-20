#!/bin/env bash

if [[ "$#" != 2 ]]; then
    echo "Usage: "$( basename $0 )" <existing run number> <seconds to run>"
    exit 0
fi

runnum=$1
seconds_to_run=$2

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

config=$( sed -r -n 's/^Config name: (\S+).*/\1/p' $recorddir/$runnum/metadata.txt )
comps=$( awk '/^Component/ { printf("%s ", $NF); }' $recorddir/$runnum/metadata.txt )

cmd="just_do_it.sh $recorddir/$runnum/boot.txt $seconds_to_run --config $config --comps \"$comps\""
echo "Executing $cmd"
eval $cmd

exit 0
