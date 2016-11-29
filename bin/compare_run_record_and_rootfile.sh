
if [[ $# != 1 ]]; then
    echo "Please pass run number as argument" >&2
    return 10
fi

runnum=$1

rootfiledir=/tmp
runrecordsdir=$HOME/run_records

rootfile=$(ls $rootfiledir/*_r$(printf "%06d" $runnum)_* )

if [[ -z $rootfile ]]; then
    echo "Unable to find root file for run #${runnum} in directory \"${rootfiledir}\"" >&2
    return 20
fi 

if [[ -z $( which config_dumper ) ]]; then
    echo "Unable to find config_dumper; you need to have your environment properly set up" >&2
    return 30
fi

temporary_daqinterface_config_file=/tmp/$(uuidgen)
temporary_metadata_file=/tmp/$(uuidgen)

config_dumper -P $file | sed -r 's/\\n/\n/g'  | sed -r '1,/run_daqinterface_config/d;/"/,$d' > $temporary_daqinterface_config_file

if [[ ! -s $temporary_daqinterface_config_file ]]; then
    echo "It appears no DAQInterface config info was saved in $file" 
fi

config_dumper -P $file | sed -r 's/\\n/\n/g'  | sed -r '1,/run_metadata/d;/"/,$d' > $temporary_metadata_file

if [[ ! -s $temporary_metadata_file ]]; then
    echo "It appears no metadata info was saved in $file" 
fi

run_records_config_file=$runrecordsdir/$runnum/config.txt
run_records_metadata_file=$runrecordsdir/$runnum/metadata.txt

if [[ ! -e $run_records_config_file ]]; then
    echo "Unable to find DAQInterface configuration file \"${run_records_config_file}\"" >&2
    return 30
fi

if [[ ! -e $run_records_metadata_file ]]; then
    echo "Unable to find metadata file \"${run_records_metadata_file}\"" >&2
    return 40
fi

res_config=$( diff --ignore-blank-lines $temporary_daqinterface_config_file $run_records_config_file )
res_metadata=$( diff --ignore-blank-lines $temporary_metadata_file $run_records_metadata_file )


if [[ -z $res_config && -z $res_metadata ]]; then
    echo "Data in $rootfile and $runrecordsdir agree"
    return 0
fi

if [[ -n $res_config ]]; then
    echo "DAQInterface configuration file info inconsistent between $rootfile and $runrecordsdir "
fi

if [[ -n $res_metadata ]]; then
    echo "Metadata file info inconsistent between $rootfile and $runrecordsdir "
fi

rm -f $temporary_daqinterface_config_file $temporary_metadata_file

return 50
