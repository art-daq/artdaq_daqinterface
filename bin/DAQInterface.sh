

# In the code below:
# -The "sed" through which tail -f is piped is there so that the tail -f doesn't show lines output during the previous DAQInterface session
# -The "nohup" is there so DAQInterface can wind down cleanly if users close its terminal
# -The "stdbuf -oL" is there so that DAQInterface output makes it into the logfile in realtime
# -The "<&-" is there to avoid hangs if users type in the terminal DAQInterface is running in (see Issue #21804)

# Make sure the logic to derive DAQInterface port # from partition #
# is the same as in daqinterface_functions.sh!

export DAQINTERFACE_PORT=$(( $ARTDAQ_BASE_PORT + $DAQINTERFACE_PARTITION_NUMBER * $ARTDAQ_PORTS_PER_PARTITION ))

expanded_daqinterface_logfilename=$( echo $( eval echo $DAQINTERFACE_LOGFILE ) )

if [[ -e $expanded_daqinterface_logfilename ]]; then
    previous_lines_of_logfile=$( wc -l $expanded_daqinterface_logfilename | awk '{print $1}' )
else
    previous_lines_of_logfile=0
fi

if (( previous_lines_of_logfile > 10 )); then
    lines_to_delete=10
else
    lines_to_delete=$previous_lines_of_logfile
fi

if [[ -z $( ps aux | grep "$DAQINTERFACE_TTY.*tail -f $expanded_daqinterface_logfilename" | grep -v grep ) ]]; then

   if (( lines_to_delete > 0 )); then
       tail -f $expanded_daqinterface_logfilename | sed -r '1,'$lines_to_delete'd' & 
   else
       tail -f $expanded_daqinterface_logfilename &
   fi

fi

nohup stdbuf -oL $ARTDAQ_DAQINTERFACE_DIR/rc/control/daqinterface.py --partition-number $DAQINTERFACE_PARTITION_NUMBER --rpc-port $DAQINTERFACE_PORT <&- >> $expanded_daqinterface_logfilename 2>&1 

pid=$( ps aux | grep "$DAQINTERFACE_TTY.*tail -f $expanded_daqinterface_logfilename" | grep -v grep | awk '{print $2}' )

if [[ -n $pid ]]; then
    kill $pid
fi

unset pid
unset expanded_daqinterface_logfilename
unset previous_lines_of_logfile
unset lines_to_delete
