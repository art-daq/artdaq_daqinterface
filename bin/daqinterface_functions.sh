
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

}

function port_disclaimer_message() {

cat <<heredoc

This command will be sent to a DAQInterface instance listening on port
$DAQINTERFACE_PORT if it exists; to send to another DAQInterface
instance, execute "export DAQINTERFACE_PORT=<desired port number>"

heredoc

}
