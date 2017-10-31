
highest_used_port=

function set_highest_used_port() {

highest_used_port=$( \
echo | awk '{ while ( ( "ps aux | grep daqinterface.py | grep -v grep" | getline ) > 0 ) { \
daqinterface_pids[$2]++ \
} \
# Grab the port a DAQInterface with a given PID is listening on with the netstat command \
for (daqpid in daqinterface_pids) { \
while ( ("netstat -apn 2>/dev/null | grep "daqpid"/python" | getline ) > 0) { \
 match($4, "[0-9]+$"); print substr($4,RSTART, RLENGTH) } # \
} \
}' | sort -n | tail -1 )

#echo "Highest used port appears to be $highest_used_port"

}

function list_daqinterfaces() {

ps aux | grep "python.*daqinterface.py" | grep -v grep | awk '{ print "DAQInterface instance was launched at "$9" by "$1" listening on port "$NF  }'

}

num_daqinterfaces=$( list_daqinterfaces | wc -l )

function port_disclaimer_message() {

if (( $num_daqinterfaces > 1 )); then

cat <<heredoc

This command will be sent to a DAQInterface instance listening on port
$DAQINTERFACE_PORT if it exists; to send to another DAQInterface
instance, execute "export DAQINTERFACE_PORT=<desired port number>"

heredoc

    list_daqinterfaces
fi

}

function daqinterface_preamble() {

if (( $num_daqinterfaces > 1)); then
    port_disclaimer_message
elif (( $num_daqinterfaces == 0)); then

cat <<heredoc

No DAQInterface instance found listening on port $DAQINTERFACE_PORT (value set 
by environment variable DAQINTERFACE_PORT); will do nothing. Existing DAQInterface
instances can be shown by the "listdaqinterfaces.sh" command 

heredoc
    exit 140
fi

}

