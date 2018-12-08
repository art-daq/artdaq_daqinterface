
import random
import string
import os
import subprocess
from subprocess import Popen
import socket
from time import sleep
import re
import sys

sys.path.append( os.environ["ARTDAQ_DAQINTERFACE_DIR"] )

from rc.control.utilities import get_pids
from rc.control.utilities import bash_unsetup_command
from rc.control.utilities import date_and_time
from rc.control.utilities import construct_checked_command
from rc.control.deepsuppression import deepsuppression


def bootfile_name_to_execname(bootfile_name):

    if "BoardReader" in bootfile_name:
        execname = "boardreader"
    elif "EventBuilder" in bootfile_name:
        execname = "eventbuilder"
    elif "DataLogger" in bootfile_name:
        execname = "datalogger"
    elif "Dispatcher" in bootfile_name:
        execname = "dispatcher"
    elif "RoutingMaster" in bootfile_name:
        execname = "routing_master"
    else:
        assert False

    return execname
    

def launch_procs_base(self):

    launch_commands_to_run_on_host = {}
    launch_commands_to_run_on_host_background = {}  # Need to run artdaq processes in the background so they're persistent outside of this function's Popen calls

    for procinfo in self.procinfos:

        if not procinfo.host in launch_commands_to_run_on_host:
            launch_commands_to_run_on_host[ procinfo.host ] = []
            launch_commands_to_run_on_host[ procinfo.host ].append(". %s/setup" % self.productsdir)  
            launch_commands_to_run_on_host[ procinfo.host ].append( bash_unsetup_command )
            launch_commands_to_run_on_host[ procinfo.host ].append("source " + self.daq_setup_script )
            launch_commands_to_run_on_host[ procinfo.host ].append("export ARTDAQ_LOG_ROOT=%s" % (self.log_directory))
            launch_commands_to_run_on_host[ procinfo.host ].append("which boardreader") # Assume if this works, eventbuilder, etc. are also there

            launch_commands_to_run_on_host_background[ procinfo.host ] = []

        launch_commands_to_run_on_host_background[ procinfo.host ].append( " %s -c \"id: %s commanderPluginType: xmlrpc rank: %s application_name: %s partition_number: %s\" & " % \
                                                   (bootfile_name_to_execname(procinfo.name), procinfo.port, procinfo.rank, procinfo.label, 
                                                    os.environ["DAQINTERFACE_PARTITION_NUMBER"]))
    
    for host in launch_commands_to_run_on_host:
        launchcmd = construct_checked_command( launch_commands_to_run_on_host[ host ] )
        launchcmd += "; "
        launchcmd += " ".join(launch_commands_to_run_on_host_background[ host ])  # Each command already terminated by ampersand

        if host != os.environ["HOSTNAME"] and host != "localhost":
            launchcmd = "ssh -f " + host + " '" + launchcmd + "'"

        self.print_log("d", "PROCESS LAUNCH COMMANDS TO EXECUTE ON %s: %s%s\n" % (host, "\n".join( launch_commands_to_run_on_host[ host ] ), "\n".join( launch_commands_to_run_on_host_background[ host ])), 2)
        
        status = Popen(launchcmd, shell=True).wait()

        if status != 0:   
            raise Exception("Status error raised by running the following commands on %s: \"\n%s\n\n\". If logfiles exist, please check them for more information. Also try running the commands interactively in a new terminal after logging into %s" %
                            (host, "\n".join(launch_commands_to_run_on_host[ host ]), host))

    return


def kill_procs_base(self):
    assert False
    # JCF, 12/29/14

    # If the PMT host hasn't been defined, we can be sure there
    # aren't yet any artdaq processes running yet (or at least, we
    # won't be able to determine where they're running!)

    if self.pmt_host is None:
        return

    # Now, the commands which will clean up the pmt.rb + its child
    # artdaq processes

    pmt_pids = get_pids("ruby.*pmt.rb -p " + str(self.pmt_port),
                             self.pmt_host)

    if len(pmt_pids) > 0:

        for pmt_pid in pmt_pids:

            cmd = "kill %s; sleep 2; kill -9 %s" % (pmt_pid, pmt_pid)

            if self.pmt_host != "localhost":
                cmd = "ssh -f " + self.pmt_host + " '" + cmd + "'"

            proc = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for procinfo in self.procinfos:

        greptoken = procinfo.name + "Main -c id: " + procinfo.port

        pids = get_pids(greptoken, procinfo.host)

        if len(pids) > 0:
            cmd = "kill -9 " + pids[0]

            if procinfo.host != "localhost":
                cmd = "ssh -f " + procinfo.host + " '" + cmd + "'"

            Popen(cmd, shell=True, stdout=subprocess.PIPE,
                  stderr=subprocess.STDOUT)

            # Check that it was actually killed

            sleep(1)

            pids = get_pids(greptoken, procinfo.host)

            if len(pids) > 0:
                self.print_log("w", "Appeared to be unable to kill %s at %s:%s during cleanup" % \
                                   (procinfo.name, procinfo.host, procinfo.port))

    self.procinfos = []

    self.kill_art_procs()

    return

def softlink_process_manager_logfiles_base(self):
    return

def find_process_manager_variable_base(self, line):
    assert False

    res = re.search(r"^\s*PMT host\s*:\s*(\S+)", line)
    if res:
        self.pmt_host = res.group(1)
        return True

    res = re.search(r"^\s*PMT port\s*:\s*(\S+)", line)
    if res:
        self.pmt_port = res.group(1)
        return True

    return False

def set_process_manager_default_variables_base(self):
    assert False
    
    if not hasattr(self, "pmt_port") or self.pmt_port is None:
        self.pmt_port = str( int(self.rpc_port) + 1 )

    undefined_vars = []
    if not hasattr(self, "pmt_host") or self.pmt_host is None:
        undefined_vars.append("PMT host")

    if len(undefined_vars) > 0:
        raise Exception("Error: the following parameters needed by DAQInterface are undefined: %s" % \
                        ( ",".join( undefined_vars ) ))

def reset_process_manager_variables_base(self):
    assert False

    self.pmt_host = None
    self.pmt_port = None

def get_process_manager_log_filenames_base(self):
    return []

def process_manager_cleanup_base(self):
    assert False

    if hasattr(self, "pmtconfigname") and os.path.exists(self.pmtconfigname):
        cmd = "rm -f %s" % (self.pmtconfigname)

        if hasattr(self, "pmt_host"):
            if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
                cmd = "ssh -f " + self.pmt_host + " '" + cmd + "'"

# check_proc_heartbeats_base() will check that the expected artdaq
# processes are up and running

def check_proc_heartbeats_base(self, requireSuccess=True):

    is_all_ok = True

    for procinfo in self.procinfos:

        greptoken = bootfile_name_to_execname(procinfo.name) + " -c .*" + procinfo.port + ".*"

        pids = get_pids(greptoken, procinfo.host)

        num_procs_found = len(pids)

        if num_procs_found != 1:
            is_all_ok = False

            if requireSuccess:
                errmsg = "Expected process " + procinfo.name + \
                    " at " + procinfo.host + ":" + \
                    procinfo.port + " not found"

                self.print_log("e", errmsg)

    if not is_all_ok and requireSuccess:
        self.heartbeat_failure = True
        self.alert_and_recover("At least one artdaq process died unexpectedly; please check messageviewer"
                               " and/or the logfiles for error messages")
        return

    return is_all_ok


def main():
    
    # JCF, Dec-7-2018

    # This is a toy version of the true Procinfo class defined within
    # the DAQInterface class, meant to be used just for testing this
    # module

    class Procinfo(object):
        def __init__(self, name, rank, host, port, label):
            self.name = name
            self.rank = rank
            self.port = port
            self.host = host
            self.label = label


    launch_procs_test = True

    if launch_procs_test:

        class MockDAQInterface:
            debug_level = 3
            productsdir = "/mu2e/ups"
            daq_setup_script = "/home/jcfree/artdaq-demo_multiple_fragments_per_boardreader/setupARTDAQDEMO"

            procinfos = []
            procinfos.append( Procinfo("BoardReader", "0", "localhost", "10100", "MockBoardReader") )
            procinfos.append( Procinfo("EventBuilder", "1", "localhost", "10101", "MockEventBuilder") )

            def print_log(self, ignore, string_to_print, ignore2):
                print string_to_print
            

        launch_procs_base( MockDAQInterface() )

if __name__ == "__main__":
    main()

                        

