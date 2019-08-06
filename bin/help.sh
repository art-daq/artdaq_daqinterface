
cat <<EOF

Before reading on, keep in mind *this is NOT a substitute for reading
the DAQInterface manual* :
https://cdcvs.fnal.gov/redmine/projects/artdaq-utilities/wiki/Artdaq-daqinterface

The following list covers the most important environment variables
used to control DAQInterface's behavior. Remember you need to set a
variable *before* launching DAQInterface; it won't pick up the change
on-the-fly. If you wish to set a variable, do so in
$DAQINTERFACE_USER_SOURCEFILE, NOT in the standard DAQInterface source
file $ARTDAQ_DAQINTERFACE_DIR/source_me


///////////////////////////////////////////////////////////////////////

DAQINTERFACE_KNOWN_BOARDREADERS_LIST: the name of the file containing
the list of possible boardreaders to select from for a run

DAQINTERFACE_LOGFILE: the name of the file which logs DAQInterface's
output to screen. Defaults to 
/tmp/daqinterface_\${USER}/DAQInterface_partition\${DAQINTERFACE_PARTITION_NUMBER}.log

DAQINTERFACE_PARTITION_NUMBER: The partition DAQInterface will run on. Defaults to 0.

DAQINTERFACE_PROCESS_MANAGEMENT_METHOD: The method DAQInterface uses
to control processes. Options are "pmt", "direct", and
"external_run_control". Defaults to "pmt".

DAQINTERFACE_PROCESS_REQUIREMENTS_LIST: The (optional) file users can
edit to control which processes are run-critical, assuming the process
management method is in "direct" mode

DAQINTERFACE_SETTINGS: The name of the file containing
unlikely-to-be-changed-often parameters controlling DAQInterface's
behavior (process timeouts, output directory for artdaq logfiles,
etc.)

//////////////////////////////////////////////////////////////////////

Keep in mind *this is NOT a substitute for reading the DAQInterface manual* :
https://cdcvs.fnal.gov/redmine/projects/artdaq-utilities/wiki/Artdaq-daqinterface

EOF
