#!/bin/env bash

config="demo"
daqcomps="component01 component02"
runs=1

env_opts_var=`basename $0 | sed 's/\.sh$//' | tr 'a-z-' 'A-Z_'`_OPTS
USAGE="\
   usage: `basename $0` [options] <file to pass on boot transition> <daq running time in seconds (0 if you want to run until ctrl-C is hit)>
examples: `basename $0` boot.txt 0
          `basename $0` --config demo_no_aggregators 20
--help        This help message
--config      Name of the configuration to use (Default: $config)
--compfile    File containing space-delimited component names to use
--comps       Space-delimited list of component names to use (Default: $daqcomps)
--bootfile    File to pass on Boot transition (overrides first parameter)
--runduration Number of seconds to run the daq (overrides second parameter)
--runs        Number of start/stop transitions to run (Default: $runs)
"

# Process script arguments and options
eval env_opts=\${$env_opts_var-} # can be args too
eval "set -- $env_opts \"\$@\""
op1chr='rest=`expr "$op" : "[^-]\(.*\)"`   && set -- "-$rest" "$@"'
op1arg='rest=`expr "$op" : "[^-]\(.*\)"`   && set --  "$rest" "$@"'
reqarg="$op1arg;"'test -z "${1+1}" &&echo opt -$op requires arg. &&echo "$USAGE" &&exit'
args= do_help=; comp_file=""; time_override=-1; boot_file=""
while [ -n "${1-}" ];do
    if expr "x${1-}" : 'x-' >/dev/null;then
        op=`expr "x$1" : 'x-\(.*\)'`; shift   # done with $1
        leq=`expr "x$op" : 'x-[^=]*\(=\)'` lev=`expr "x$op" : 'x-[^=]*=\(.*\)'`
        test -n "$leq"&&eval "set -- \"\$lev\" \"\$@\""&&op=`expr "x$op" : 'x\([^=]*\)'`
        case "$op" in
            \?*|h*)     eval $op1chr; do_help=1;;
            -help)      eval $op1arg; do_help=1;;
            -config)    eval $reqarg; config=$1; shift;;
            -comps)     eval $reqarg; daqcomps=$1; shift;;
            -compfile)  eval $reqarg; comp_file=$1; shift;;  
            -runduration) eval $reqarg; time_override=$1; shift;;
            -bootfile)  eval $reqarg; boot_file=$1; shift;;
			-runs)      eval $reqarg; runs=$1; shift;;
            *)          echo "Unknown option -$op"; do_help=1;;
        esac
    else
        aa=`echo "$1" | sed -e"s/'/'\"'\"'/g"` args="$args '$aa'"; shift
    fi
done
eval "set -- $args \"\$@\""; unset args aa
set -u   # complain about uninitialed shell variables - helps development

if [[ "x$comp_file" != "x" ]]; then
  daqcomps=`cat $comp_file`
fi

echo "Configuration: ${config}, Components: ${daqcomps}, Remaining Args: $#"

test -n "${do_help-}" -o $# -ge 3 && echo "$USAGE" && exit

scriptdir="$(dirname "$0")"

if [[ "x$boot_file" == "x" ]]; then
  daqintconfig=$1
else
  daqintconfig=${boot_file}
fi
if [ $time_override -eq -1 ]; then
  daq_time_in_seconds=$2
else
  daq_time_in_seconds=$time_override
fi

. $ARTDAQ_DAQINTERFACE_DIR/bin/diagnostic_tools.sh

rm -f /tmp/listconfigs_${USER}.txt
$scriptdir/listconfigs.sh 

if [[ "$?" == "0" ]]; then
    config=$( grep "^${config}[0-9]*$" /tmp/listconfigs_${USER}.txt  | sort -n | tail -1 )
else
    echo "There was a problem getting a list of configurations" >&2
    exit 110
fi


starttime=$(date +%s)



root_output_dir="/tmp"

if ! [[ $daq_time_in_seconds =~ ^[0-9-]+$ ]]; then
    echo 'Entered value for daq running time of "'$daq_time_in_seconds'" does not appear to be an integer'
    exit 10
fi

highest_runnum=$( ls -1 $recorddir | sort -n | tail -1 )
runnum=$(( highest_runnum + 1 ))

# See below for definition of "clean_shutdown" function

trap "clean_shutdown" SIGHUP SIGINT SIGTERM

daqutils_script=$scriptdir/daqutils.sh

if ! [[ -e $daqutils_script ]]; then 
     echo $(date) "Unable to source $daqutils_script - script not found" >&2
     exit 30
else   
     . $daqutils_script
fi   


# And now define the main body of code (this function is not actually
# called until the very bottom of the script, in order to be able to
# use functions in the body of the main() function that aren't defined
# until lower in the script)

function main() {

    res=$( ps aux | grep -E "python.*daqinterface.py" | grep -v grep )

    if [[ -z $res ]]; then
	echo 
	echo "DAQInterface does not appear to be running, will exit.." >&2
	exit 40
    fi

    echo -n "Checking that the DAQ is in the \"stopped\" state..."

    state_true="0"
    check_for_state "stopped" state_true

    if [[ "$state_true" == "1" ]]; then
	echo "success"
    else
	echo
	echo "DAQ does not appear to be in the \"stopped\" state, exiting..."
	exit 50
    fi

    $scriptdir/setdaqcomps.sh $daqcomps

    $scriptdir/send_transition.sh boot $daqintconfig

    wait_until_no_longer booting

    state_true="0"
    check_for_state "booted" state_true

    if [[ "$state_true" != "1" ]]; then
	echo "DAQ failed to enter booted state; exiting $0"
	exit 51
    fi

    sleep 2
    #read -n 1 -s -r -p "Press any key to configure"
    # Initialize the DAQ

    config_cntr=0
    
    while (( $config_cntr < 1 )); do 

	config_cntr=$(( config_cntr + 1 ))
    $scriptdir/send_transition.sh config $config

    wait_until_no_longer configuring

    state_true="0"
    check_for_state "ready" state_true

    if [[ "$state_true" != "1" ]]; then
	echo "DAQ failed to enter ready state; exiting $0"
	exit 60
    fi

    done

    # Start the DAQ, and run it for the requested amount of time
	counter=0
	while [ $counter -lt $runs ]; do
		#read -n 1 -s -r -p "Press any key to start"
		$scriptdir/send_transition.sh start

		wait_until_no_longer starting

		state_true="0"
		check_for_state "running" state_true

		if [[ "$state_true" != "1" ]]; then
			echo "DAQ failed to enter running state; exiting $0"
			exit 70
		fi

    
		if [[ $daq_time_in_seconds > 0 ]]; then
			echo "Will acquire data for $daq_time_in_seconds seconds"
			sleep $daq_time_in_seconds
		else
			echo "Will acquire data until Ctrl-C is hit"
			sleep 10000000000
		fi

		# Stop the DAQ
    
		state_true="0"
		check_for_state "running" state_true

		if [[ "$state_true" == "1" ]]; then
			#read -n 1 -s -r -p "Press any key to stop"
			$scriptdir/send_transition.sh stop
			wait_until_no_longer stopping
		fi

		counter=$(($counter + 1))
	done

	clean_shutdown
}

# clean_shutdown() will be called either (A) after the DAQ has run for
# the user-requested period of time, or (B) after ctrl-C has been hit
# (in which case it's called by the external_termination() handler
# function. It will issue a "stop" if it sees the DAQ is in the
# "running" state; either way, it issues a "terminate"

function clean_shutdown() {

    echo "Entered clean_shutdown"

    # Stop the DAQ, if necessary
    
    state_true="0"
    check_for_state "running" state_true

    if [[ "$state_true" == "1" ]]; then
    #read -n 1 -s -r -p "Press any key to stop"
	$scriptdir/send_transition.sh stop
	wait_until_no_longer stopping
    fi

    sleep 1

    state_true="0"
    check_for_state "ready" state_true

    if [[ "$state_true" != "1" ]]; then
	echo "DAQ unexpectedly not in ready state; exiting "$( basename $0)
	exit 80
    fi

    # $scriptdir/send_transition.sh shutdown
    # wait_until_no_longer shutting

    # sleep 1

    # state_true="0"
    # check_for_state "booted" state_true

    # if [[ "$state_true" != "1" ]]; then
    # 	echo "DAQ unexpectedly not in booted state; exiting "$( basename $0)
    # 	exit 81
    # fi

    if true; then
	
    #read -n 1 -s -r -p "Press any key to shutdown"
	$scriptdir/send_transition.sh terminate

	wait_until_no_longer terminating

	state_true="0"
	check_for_state "stopped" state_true

	if [[ "$state_true" != "1" ]]; then
	    echo "DAQ unexpectedly not in stopped state;  exiting "$( basename $0)
	    exit 90
	fi
    else
	echo "Skipping the terminate step"
    fi
}

function check_output_file() {

    local runtoken=$( awk 'BEGIN{ printf("r%06d", '$runnum')}' )
    
    local glob=$root_output_dir/*${runtoken}*.root
    local output_file=$( ls -tr1 $glob | tail -1 )    

    if [[ -n $output_file ]]; then
	ls -l $output_file
	return
    else
	echo "No file in $root_output_dir matches glob $glob" >&2
	exit 100
    fi
}

function check_run_records() {

    if [[ ! -d $recorddir/$runnum ]]; then
	echo "Unable to find expected run records subdirectory $recorddir/$runnum" >&2
	exit 200
    fi

    echo "Contents of $recorddir/$runnum :"
    ls -ltr $recorddir/$runnum 
}

function check_event_count() {
    
    metadata_file=$recorddir/$runnum/metadata.txt

    if [[ ! -e $metadata_file ]]; then
	echo "Unable to find expected metadata file $metadata_file" >&2
	return
    fi

    events_in_metadata=$( awk '/^\s*Total events/ { print $NF }' $metadata_file )

    if [[ -z $events_in_metadata ]]; then
	echo "Unable to find value for total events in $metadata_file" >&2
	return
    fi

    events_in_rootfiles=$( $( dirname $0 )/rootfile_event_count.sh $runnum )

    if ! [[ "$?" == "0" ]]; then 
    	echo "Unable to determine the # of events from the expected *.root files" >&2
    	return
    fi

    if [[ "$events_in_metadata" == "$events_in_rootfiles" ]]; then
    	echo "Event count in saved metadata and event count in *.root files agree (${events_in_metadata})" 
    else
    	echo "Event count in saved metadata (${events_in_metadata}) and event count in *.root files (${events_in_rootfiles}) don't agree" >&2
    fi

}


main $@

#echo
#check_output_file
echo
check_run_records
echo
$( dirname $0 )/compare_run_record_and_rootfile.sh $runnum
echo
check_event_count
echo

endtime=$(date +%s)
runningtime=$(( $endtime - $starttime ))

echo $(basename $0)" completed; script was up for $runningtime seconds"

exit 0
