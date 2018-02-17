

function list_daqinterfaces() {

ps aux | grep "python.*daqinterface.py" | grep -v grep | awk '{ print "DAQInterface instance was launched at "$9" by "$1" listening on port "$NF  }'

}

num_daqinterfaces=$( list_daqinterfaces | wc -l )

function get_highest_used_port() {

highest_used_port=$( ps aux | grep "python.*daqinterface.py" | grep -v grep | awk '{print $NF}' | sort | tail -1 )

if [[ -n $highest_used_port ]]; then
    echo $highest_used_port
else
    echo 5560
fi

}



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

