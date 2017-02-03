#!/bin/env bash

# JCF, Feb-3-2017

# Be aware that:

# This script was originally tested (i.e., tested to see that it
# performs tests correctly) using artdaq-demo v2_08_04

# This script expects simple_test_config/demo/component01_hw_cfg.fcl to exist

# This script expects the variables "change_after_N_seconds" and
# "nADCcounts_after_N_seconds" to exist in that file, but to be
# commented out

# This script will modify simple_test_config/demo/component01_hw_cfg.fcl

# Also, I'd like to add a timed exception throw at some point, but
# that functionality doesn't (yet) exist in artdaq-demo

# Could also try overwhelming the system by setting
# nADCcounts_after_N_seconds to a huge value

if [[ ! -e bin/just_do_it.sh ]]; then
    echo "Can't find bin/just_do_it.sh; are you in the base directory of artdaq-utilities-daqinterface?" >&2
    exit 10
fi

logfile=/tmp/daqinterface/DI.log
cmd="tee -a $logfile"

res=$(ps aux | grep "$cmd" | grep -v grep )

if [[ -z $res ]]; then
    echo "Failed to see a running instance of \"$cmd\" needed to save DAQInterface output; exiting..." >&2
    exit 20
fi

# Make sure this isn't a shorter time period than when the ToySimulator's pathologies are timed to kick in
runtime=10

echo "WILL TRY REGULAR RUNNING FOR $runtime SECONDS "

./bin/just_do_it.sh $runtime

if [[ "$?" != "0" ]]; then
    echo "just_do_it.sh RETURNED NONZERO FOR REGULAR RUNNING; SKIPPING FURTHER TESTS" >&2
    exit 30
fi

echo "WILL TRY SIMULATING A HANG FROM ONE OF THE BOARDREADERS"

boardreader_fhicl=simple_test_config/demo/component01_hw_cfg.fcl

for needed_variable in change_after_N_seconds nADCcounts_after_N_seconds ; do

    if [[ -z $( grep -l $needed_variable $boardreader_fhicl ) ]]; then
	echo "Unable to find needed variable \"$needed_variable\" in ${boardreader_fhicl}; exiting..." >&2
	exit 40
    fi
done

sed -r -i 's/.*change_after_N_seconds.*/change_after_N_seconds: 5/' $boardreader_fhicl
sed -r -i 's/.*nADCcounts_after_N_seconds.*/nADCcounts_after_N_seconds: -1/' $boardreader_fhicl

./bin/just_do_it.sh $runtime

echo "WILL RUN INDEFINITELY - THIS GIVES YOU AN OPPORTUNITY TO EXTERNALLY KILL AN ARTDAQ PROCESS TO SEE WHAT HAPPENS"

sed -r -i 's/.*change_after_N_seconds.*/#change_after_N_seconds: 5/' $boardreader_fhicl
sed -r -i 's/.*nADCcounts_after_N_seconds.*/#nADCcounts_after_N_seconds: -1/' $boardreader_fhicl

./bin/just_do_it.sh 0

exit 0
