#!/bin/env bash

if [[ $# != 1 ]]; then
    echo "Please pass run number as argument" >&2
    exit 10
fi

runnum=$1

scriptdir="$(dirname "$0")"
. $scriptdir/package_setup.sh art

art_retval=$?

if [[ "$art_retval" != "0" ]]; then
    echo "Problem attempting to setup art package" >&2
    exit 40
fi

rootfiledir=/tmp
runrecordsdir=$HOME/run_records

rootfile=$(ls -tr1 $rootfiledir/*_r$(printf "%06d" $runnum)_* | tail -1 )

if [[ -z $rootfile ]]; then
    echo "Unable to find root file for run #${runnum} in directory \"${rootfiledir}\"" >&2
    exit 20
fi 

if [[ -z $( which config_dumper ) ]]; then
    echo
    echo "Unable to find config_dumper; you need to have your environment properly set up" >&2
    exit 30
fi

temporary_daqinterface_config_file=/tmp/$(uuidgen)
temporary_metadata_file=/tmp/$(uuidgen)

echo "NOTE: erasing any output to stderr from config_dumper; as long
as config_dumper works correctly this won't affect the results of the
test"

config_dumper -P $rootfile 2> /dev/null | sed -r 's/\\n/\n/g'  | sed -r '1,/run_daqinterface_config/d;/^\s*"\s*$/,$d;s/\\"/"/g'  > $temporary_daqinterface_config_file 

if [[ ! -s $temporary_daqinterface_config_file ]]; then
    echo "It appears no DAQInterface config info was saved in $rootfile" 
fi

config_dumper -P $rootfile 2> /dev/null  | sed -r 's/\\n/\n/g'  | sed -r '1,/run_metadata/d;/"/,$d' > $temporary_metadata_file 

if [[ ! -s $temporary_metadata_file ]]; then
    echo "It appears no metadata info was saved in $rootfile" 
fi

run_records_config_file=$runrecordsdir/$runnum/config.txt
run_records_metadata_file=$runrecordsdir/$runnum/metadata.txt

if [[ ! -e $run_records_config_file ]]; then
    echo "Unable to find DAQInterface configuration file \"${run_records_config_file}\"" >&2
    exit 30
fi

if [[ ! -e $run_records_metadata_file ]]; then
    echo "Unable to find metadata file \"${run_records_metadata_file}\"" >&2
    exit 40
fi

res_config=$( diff --ignore-blank-lines $temporary_daqinterface_config_file $run_records_config_file )
res_metadata=$( diff --ignore-blank-lines $temporary_metadata_file $run_records_metadata_file )


if [[ -z $res_config && -z $res_metadata ]]; then
    echo "Data in $rootfile and $runrecordsdir/$runnum agree"
    rm -f $temporary_daqinterface_config_file $temporary_metadata_file
    exit 0
fi

if [[ -n $res_config ]]; then
    echo "DAQInterface configuration file info inconsistent between $rootfile and $runrecordsdir/$runnum "
fi

if [[ -n $res_metadata ]]; then
    echo "Metadata file info inconsistent between $rootfile and $runrecordsdir/$runnum "
fi

rm -f $temporary_daqinterface_config_file $temporary_metadata_file

exit 50
