
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
from rc.control.utilities import obtain_messagefacility_fhicl
from rc.control.utilities import make_paragraph
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

# JCF, Dec-18-18
    
# For the purposes of more helpful error reporting if DAQInterface
# determines that launch_procs_base ultimately failed, have
# launch_procs_base return a dictionary whose keys are the hosts on
# which it ran commands, and whose values are the list of commands run
# on those hosts

def launch_procs_base(self):

    if self.have_artdaq_mfextensions():
        messagefacility_fhicl_filename = obtain_messagefacility_fhicl()

        for host in set([procinfo.host for procinfo in self.procinfos]):
            if host != "localhost" and host != os.environ["HOSTNAME"]:
                cmd = "scp -p %s %s:%s" % (messagefacility_fhicl_filename, host, messagefacility_fhicl_filename)
                status = Popen(cmd, shell=True).wait()

                if status != 0:
                    raise Exception("Status error raised in %s executing \"%s\"" % (launch_procs_base.__name__, cmd))


    launch_commands_to_run_on_host = {}
    launch_commands_to_run_on_host_background = {}  # Need to run artdaq processes in the background so they're persistent outside of this function's Popen calls
    launch_commands_on_host_to_show_user = {} # Don't want to clobber a pre-existing logfile or clutter the commands via "$?" checks
            
    self.launch_attempt_file = "/tmp/launch_attempt_%s_partition%s" % (os.environ["USER"], os.environ["DAQINTERFACE_PARTITION_NUMBER"])

    for procinfo in self.procinfos:

        if not procinfo.host in launch_commands_to_run_on_host:

            launch_commands_to_run_on_host[ procinfo.host ] = []
            launch_commands_to_run_on_host_background[ procinfo.host ] = []
            launch_commands_on_host_to_show_user[ procinfo.host ] = []

            launch_commands_to_run_on_host[ procinfo.host ].append("set +C")  
            launch_commands_to_run_on_host[ procinfo.host ].append("echo > %s" % (self.launch_attempt_file))
            launch_commands_to_run_on_host[ procinfo.host ].append(". %s/setup >> %s 2>&1 " % (self.productsdir, self.launch_attempt_file))
            launch_commands_to_run_on_host[ procinfo.host ].append( bash_unsetup_command )
            launch_commands_to_run_on_host[ procinfo.host ].append("source %s >> %s 2>&1 " % (self.daq_setup_script, self.launch_attempt_file ))
            launch_commands_to_run_on_host[ procinfo.host ].append("export ARTDAQ_LOG_ROOT=%s" % (self.log_directory))
            if self.have_artdaq_mfextensions():
                launch_commands_to_run_on_host[ procinfo.host ].append("export ARTDAQ_LOG_FHICL=%s" % (messagefacility_fhicl_filename))
            launch_commands_to_run_on_host[ procinfo.host ].append("which boardreader >> %s 2>&1 " % (self.launch_attempt_file)) # Assume if this works, eventbuilder, etc. are also there
            #launch_commands_to_run_on_host[ procinfo.host ].append("setup valgrind v3_13_0")
	    #launch_commands_to_run_on_host[ procinfo.host ].append("export LD_PRELOAD=libasan.so")
	    #launch_commands_to_run_on_host[ procinfo.host ].append("export ASAN_OPTIONS=alloc_dealloc_mismatch=0")

            for command in launch_commands_to_run_on_host[ procinfo.host ]:
                res = re.search(r"^([^>]*).*%s.*$" % (self.launch_attempt_file), command)
                if not res:
                    launch_commands_on_host_to_show_user[ procinfo.host ].append( command)
                else:
                    launch_commands_on_host_to_show_user[ procinfo.host].append( res.group(1) )
                    

        base_launch_cmd = "%s -c \"id: %s commanderPluginType: xmlrpc rank: %s application_name: %s partition_number: %s\"" % \
                          (bootfile_name_to_execname(procinfo.name), procinfo.port, procinfo.rank, procinfo.label, 
                           os.environ["DAQINTERFACE_PARTITION_NUMBER"])
        #base_launch_cmd = "valgrind --tool=callgrind %s" % (base_launch_cmd)
        launch_cmd = "%s >> %s 2>&1 & " % (base_launch_cmd, self.launch_attempt_file)

        launch_commands_to_run_on_host_background[ procinfo.host ].append( launch_cmd )
        launch_commands_on_host_to_show_user[ procinfo.host].append( "%s &" % (base_launch_cmd) )

    print
    for host in launch_commands_to_run_on_host:

        self.print_log("d", "Trying to launch processes on %s" % (host), 2)

        # Before we try launching the processes, let's make sure there
        # aren't any pre-existing processes listening on the same
        # ports

        grepped_lines = []
        preexisting_pids = get_pids("\|".join([ "%s.*id:\s\+%s" % 
                                                (bootfile_name_to_execname(procinfo.name), procinfo.port) for \
                                                procinfo in self.procinfos if procinfo.host == host ]),
                                    host,
                                    grepped_lines)
        if len(preexisting_pids) > 0:
            self.print_log("e", make_paragraph("On host %s, found artdaq process(es) already existing which use the ports DAQInterface was going to use; this may be the result of an improper cleanup from a prior run: " % (host)))
            self.print_log("e", "\n" + "\n".join(grepped_lines))
            self.print_log("i", "...note that the process(es) may get automatically cleaned up during DAQInterface recovery\n")
            raise Exception(make_paragraph("DAQInterface found previously-existing artdaq processes using desired ports; see error message above for details"))
        

        launchcmd = construct_checked_command( launch_commands_to_run_on_host[ host ] )
        launchcmd += "; "
        launchcmd += " ".join(launch_commands_to_run_on_host_background[ host ])  # Each command already terminated by ampersand

        if host != os.environ["HOSTNAME"] and host != "localhost":
            launchcmd = "ssh -f " + host + " '" + launchcmd + "'"

        self.print_log("d", "PROCESS LAUNCH COMMANDS TO EXECUTE ON %s:\n%s\n" % (host, "\n".join(launch_commands_on_host_to_show_user[host])), 2)
        
        with deepsuppression(self.debug_level < 4):
            status = Popen(launchcmd, shell=True, preexec_fn=os.setpgrp).wait()

        if status != 0:   
            self.print_log("e", "Status error raised in attempting to launch processes on %s, to investigate, see %s:%s for output" % (host, host, self.launch_attempt_file))
            self.print_log("i", make_paragraph("You can also try running again with the \"debug level\" in the boot file set to 4. Otherwise, you can recreate what DAQInterface did by performing a clean login to %s, source-ing the DAQInterface environment and executing the following:" % (host)))
            self.print_log("i", "\n" + "\n".join(launch_commands_on_host_to_show_user[host]) + "\n")
            raise Exception("Status error raised attempting to launch processes on %s; scroll up for more detail" % (host))

    return launch_commands_on_host_to_show_user

def process_launch_diagnostics_base(self, procinfos_of_failed_processes):
    for host in set([procinfo.host for procinfo in procinfos_of_failed_processes]):
        self.print_log("e", "\nOutput of unsuccessful attempted process launch on %s can be found in file %s:%s" % (host, host, self.launch_attempt_file))



def kill_procs_base(self):

    for host in set([procinfo.host for procinfo in self.procinfos]):

        artdaq_pids, labels_of_found_processes = get_pids_and_labels_on_host(host, self.procinfos)
        if len(artdaq_pids) > 0:
            self.print_log("i", "%s: Found the following processes on %s, will attempt to kill them: %s" % \
                           (date_and_time(), host, " ".join( labels_of_found_processes ) ), 0)

            cmd = "kill %s" % (" ".join(artdaq_pids))
            if host != "localhost" and host != os.environ["HOSTNAME"]:
                cmd = "ssh -x " + host + " '" + cmd + "'"

            Popen(cmd, shell=True, stdout=subprocess.PIPE,
                  stderr=subprocess.STDOUT).wait()
            self.print_log("d", "%s: Finished (attempted) kill of the following processes on %s: %s" % \
                           (date_and_time(), host, " ".join( labels_of_found_processes ) ), 2)

        art_pids = get_pids("art -c .*partition_%s" % os.environ["DAQINTERFACE_PARTITION_NUMBER"], host)

        if len(art_pids) > 0:

            cmd = "kill -9 %s" % (" ".join( art_pids ) )   # JCF, Dec-8-2018: the "-9" is apparently needed...

            if host != "localhost" and host != os.environ["HOSTNAME"]:
                cmd = "ssh -x " + host + " '" + cmd + "'"

            self.print_log("d", "%s: About to kill the artdaq-associated art processes on %s" % (date_and_time(), host), 2)
            Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).wait()
            self.print_log("d", "%s: Finished kill of the artdaq-associated art processes on %s" % (date_and_time(), host), 2)

    sleep(1)

    for host in set([procinfo.host for procinfo in self.procinfos]):

        artdaq_pids, labels_of_found_processes = get_pids_and_labels_on_host(host, self.procinfos)    

        if len(artdaq_pids) > 0:
            self.print_log("w", make_paragraph("Despite receiving a termination signal, the following artdaq processes on %s were not killed, so they'll be issued a SIGKILL: %s" % (host, " ".join(labels_of_found_processes))))
            cmd = "kill -9 %s" % (" ".join(artdaq_pids))
            if host != "localhost" and host != os.environ["HOSTNAME"]:
                cmd = "ssh -x " + host + " '" + cmd + "'"
            Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).wait()

    self.procinfos = []

    return

def softlink_process_manager_logfiles_base(self):
    return

def find_process_manager_variable_base(self, line):
    return False

def set_process_manager_default_variables_base(self):
    pass # There ARE no persistent variables specific to direct process management

def reset_process_manager_variables_base(self):
    pass

def get_process_manager_log_filenames_base(self):
    return []

def process_manager_cleanup_base(self):
    pass

def get_pid_for_process_base(self, procinfo):

    assert procinfo in self.procinfos

    greptoken = bootfile_name_to_execname(procinfo.name) + " -c .*" + procinfo.port + ".*"

    grepped_lines = []
    pids = get_pids(greptoken, procinfo.host, grepped_lines)

    ssh_pids = get_pids("ssh .*" + greptoken, procinfo.host)
            
    cleaned_pids = [ pid for pid in pids if pid not in ssh_pids ]

    if len(cleaned_pids) == 1:    
        return cleaned_pids[0]
    elif len(cleaned_pids) == 0:
        return None
    else:
        for grepped_line in grepped_lines:
            print grepped_line

        print "Appear to have duplicate processes for %s on %s, pids: %s" % (procinfo.label, procinfo.host, " ".join( pids ))

    return None

def mopup_process_base(self, procinfo):

    if procinfo.host != "localhost" and procinfo.host != os.environ["HOSTNAME"]:
        on_other_node = True
    else: 
        on_other_node = False

    pid = get_pid_for_process_base(self, procinfo)

    if pid is not None:
        cmd = "kill %s" % (pid)
        
        if on_other_node:
            cmd = "ssh -x %s '%s'" % (procinfo.host, cmd)

        status = Popen(cmd, shell=True).wait()
        sleep(1)

        if get_pid_for_process_base(self, procinfo) is not None:
            cmd = "kill -9 %s > /dev/null 2>&1" % (pid)
            
            if on_other_node:
                cmd = "ssh -x %s '%s'" % (procinfo.host, cmd)
            
            self.print_log("w", "A standard kill of the artdaq process %s on %s didn't work; resorting to a kill -9" % \
                           (procinfo.label, procinfo.host))
            Popen(cmd, shell=True).wait()

    # Will need to perform some additional cleanup (clogged ports, zombie art processes, etc.)

    ssh_mopup_ok = True  
    related_process_mopup_ok = True

    # Need to deal with the lingering ssh command if the lost process is on a remote host
    if on_other_node:

        # Mopup the ssh call on this side
        ssh_grepstring = "ssh.*%s.*%s -c.*%s" % (procinfo.host, bootfile_name_to_execname(procinfo.name),
                                                procinfo.label) 
        pids = get_pids(ssh_grepstring)

        if len(pids) == 1:
            Popen("kill %s > /dev/null 2>&1" % (pids[0]), shell=True).wait()
            pids = get_pids(ssh_grepstring)
            if len(pids) == 1:
                ssh_mopup_ok = False
        elif len(pids) > 1:
            ssh_mopup_ok = False

    # And take out the process(es) associated with the artdaq process via its listening port (e.g., the art processes)
    
    cmd = "kill %s > /dev/null 2>&1" % (" ".join(get_related_pids_for_process(procinfo)))
    
    if on_other_node:
        cmd = "ssh -x %s '%s'" % (procinfo.host, cmd)

    Popen(cmd, shell=True).wait()

    unkilled_related_pids = get_related_pids_for_process(procinfo)
    if len(unkilled_related_pids) == 0:
        related_process_mopup_ok = True
    else:
        related_process_mopup_ok = False
        self.print_log("w", make_paragraph("Warning: unable to normally kill process(es) associated with now-deceased artdaq process %s; on %s the following pid(s) remain: %s. Will now resort to kill -9 on these processes." % (procinfo.label, procinfo.host, " ".join(unkilled_related_pids))))
        cmd = "kill -9 %s > /dev/null 2>&1 " % (" ".join(unkilled_related_pids))

        if on_other_node:
            cmd = "ssh -x %s '%s'" % (procinfo.host, cmd)
        
        Popen(cmd, shell=True).wait()

    if not ssh_mopup_ok:
        self.print_log("w", make_paragraph("There was a problem killing the ssh process to %s related to the deceased artdaq process %s at %s:%s; there *may* be issues with the next run using that host and port as a result" % (procinfo.host, procinfo.label, procinfo.host, procinfo.port)))

    if not related_process_mopup_ok:
        self.print_log("w", make_paragraph("At least some of the processes on %s related to deceased artdaq process %s at %s:%s (e.g. art processes) had to be forcibly killed; there *may* be issues with the next run using that host and port as a result" % (procinfo.host, procinfo.label, procinfo.host, procinfo.port)))

    

# If you change what this function returns, you should rename it for obvious reasons
def get_pids_and_labels_on_host(host, procinfos):

    greptokens = []
    
    for procinfo in [pi for pi in procinfos if pi.host == host]:
        greptokens.append( "[0-9]:[0-9][0-9]\s\+" + bootfile_name_to_execname(procinfo.name) + " -c .*" + procinfo.port + ".*" ) 

    greptoken = "\|".join(greptokens)
    
    greptoken = "[0-9]:[0-9][0-9]\s\+\(%s\).*application_name.*partition_number" % \
                ("\|".join(set([bootfile_name_to_execname(procinfo.name) for procinfo in procinfos])))

    #greptoken = "[0-9]:[0-9][0-9]\s\+valgrind.*\(%s\).*application_name.*partition_number" % \
    #            ("\|".join(set([bootfile_name_to_execname(procinfo.name) for procinfo in procinfos])))


    grepped_lines = []
    pids = get_pids(greptoken, host, grepped_lines)

    labels_of_found_processes = []

    for line in grepped_lines:
        res = re.search(r"application_name:\s+(\S+)", line)
        assert res
        labels_of_found_processes.append( res.group(1) )
        
    return pids, labels_of_found_processes


def get_related_pids_for_process(procinfo):
    related_pids = []

    netstat_cmd = "netstat -alpn | grep %s" % (procinfo.port)

    if procinfo.host != "localhost" and procinfo.host != os.environ["HOSTNAME"]:
        netstat_cmd = "ssh -x %s '%s'" % (procinfo.host, netstat_cmd)

    proc = Popen(netstat_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for procline in proc.stdout.readlines():
        res = re.search(r"([0-9]+)/(.*)", procline.split()[-1])
        if res:
            pid = res.group(1)
            pname = res.group(2)
            if "python" not in pname:  # Don't want DAQInterface to kill itself off...
                related_pids.append( res.group(1) )
    return set(related_pids)



# check_proc_heartbeats_base() will check that the expected artdaq
# processes are up and running

def check_proc_heartbeats_base(self, requireSuccess=True):

    is_all_ok = True

    procinfos_to_remove = []
    found_processes = []

    for host in set([procinfo.host for procinfo in self.procinfos]):
        
        pids, labels_of_found_processes = get_pids_and_labels_on_host(host, self.procinfos)
        
        for procinfo in [procinfo for procinfo in self.procinfos if procinfo.host == host]:
            if procinfo.label in labels_of_found_processes:
                found_processes.append( procinfo )
            else:
                is_all_ok = False

                if requireSuccess:
                    self.print_log("e", "%s: Appear to have lost process with label %s on host %s" % (date_and_time(), procinfo.label, procinfo.host))
                    procinfos_to_remove.append( procinfo )

                    mopup_process_base(self, procinfo)
    
    if not is_all_ok and requireSuccess:
        for procinfo in procinfos_to_remove:
            self.procinfos.remove( procinfo )
            if procinfo.label in self.critical_processes_list:
                self.print_log("e", "Lost process \"%s\" is in the critical process list (%s); will now end the run and go to the Stopped state", procinfo.label, os.environ["DAQINTERFACE_CRITICAL_PROCESSES_LIST"] )
                raise Exception("\nCritical process \"%s\" lost" % (procinfo.label))

        print
        self.print_log("i", "Processes remaining:\n%s" % ("\n".join( [procinfo.label for procinfo in self.procinfos])))
        return

    if is_all_ok:
        assert len(found_processes) == len(self.procinfos)

    return found_processes


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

                        

