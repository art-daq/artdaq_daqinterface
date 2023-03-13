
import random
import string
import os
import subprocess
from subprocess import Popen
import socket
from time import sleep
import re

from rc.control.utilities import get_pids
from rc.control.utilities import bash_unsetup_command
from rc.control.utilities import date_and_time
from rc.control.utilities import construct_checked_command
from rc.control.utilities import obtain_messagefacility_fhicl
from rc.control.utilities import upsproddir_from_productsdir
from rc.control.utilities import make_paragraph
from rc.control.deepsuppression import deepsuppression

# JCF, 8/11/14

# launch_procs_base() will create the artdaq processes

# JCF, Dec-18-2018

# For the purposes of more helpful error reporting if DAQInterface
# determines that launch_procs_base ultimately failed, have
# launch_procs_base return a dictionary whose keys are the hosts on
# which it ran commands, and whose values are the list of commands run
# on those hosts


def launch_procs_base(self):

    # JCF, Sep-3-2019

    # First, as per Issue #22372, mop up any stale shared memory segments on the hosts we'll be running on
    
    with deepsuppression(self.debug_level < 4):
        for host in set([procinfo.host for procinfo in self.procinfos]):
            cmd = "%s/bin/mopup_shmem.sh %s --force" % (
                os.environ["ARTDAQ_DAQINTERFACE_DIR"],
                os.environ["DAQINTERFACE_PARTITION_NUMBER"],
            )
            if host != os.environ["HOSTNAME"] and host != "localhost":
                cmd = "ssh -f " + host + " '" + cmd + "'"
                Popen(cmd, shell=True)

    greptoken = "pmt.rb -p " + self.pmt_port
    pids = get_pids(greptoken, self.pmt_host)

    if len(pids) != 0:
        raise Exception(
            '"pmt.rb -p %s" was already running on %s' % (self.pmt_port, self.pmt_host)
        )

    self.print_log("d", "Assuming daq package is in " + self.daq_dir, 2)

    # We'll use the desired features of the artdaq processes to
    # create a text file which will be passed to artdaq's pmt.rb
    # program

    self.pmtconfigname = "/tmp/pmtConfig." + "".join(
        random.choice(string.digits) for _ in range(5)
    )

    outf = open(self.pmtconfigname, "w")

    # The rank MPI assigns the artdaq process corresponds to the order it appears in the pmtConfig file below

    for procinfo in sorted( self.procinfos, key=lambda procinfo: int(procinfo.rank) ) :
        outf.write(procinfo.name + "Main!")

        if procinfo.host != "localhost":
            host_to_write = procinfo.host
        else:
            host_to_write = os.environ["HOSTNAME"]

        outf.write(
            host_to_write
            + "!  id: "
            + procinfo.port
            + " commanderPluginType: xmlrpc application_name: "
            + str(procinfo.label)
            + " partition_number: "
            + str(self.partition_number)
            + "\n"
        )

    outf.close()

    if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
        raise Exception(
            '"PMT host" currently needs to be set to "localhost" or "%s" in the boot file'
            % (os.environ["HOSTNAME"])
        )

    if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
        status = Popen(
            "scp -p " + self.pmtconfigname + " " + self.pmt_host + ":/tmp", shell=True
        ).wait()

        if status != 0:
            raise Exception(
                "Exception in DAQInterface: unable to copy "
                + self.pmtconfigname
                + " to "
                + self.pmt_host
                + ":/tmp"
            )

    self.launch_cmds = []
    self.launch_cmds.append(
        'export PRODUCTS="%s"; . %s/setup'
        % (self.productsdir, upsproddir_from_productsdir(self.productsdir))
    )
    self.launch_cmds.append( bash_unsetup_command )
    self.launch_cmds.append("source %s for_running"%(self.daq_setup_script,) )
    self.launch_cmds.append("which pmt.rb")  # Sanity check capable of returning nonzero

    # 30-Jan-2017, KAB: increased the amount of time that pmt.rb provides daqinterface
    # to react to errors.  This should be longer than the sum of the individual
    # process timeouts.
    self.launch_cmds.append("export ARTDAQ_PROCESS_FAILURE_EXIT_DELAY=120")

    messagefacility_fhicl_filename = obtain_messagefacility_fhicl(
        self.have_artdaq_mfextensions()
    )

    for host in set([procinfo.host for procinfo in self.procinfos]):
        if host != "localhost" and host != os.environ["HOSTNAME"]:
            cmd = "scp -p %s %s:%s" % (
                messagefacility_fhicl_filename,
                host,
                messagefacility_fhicl_filename,
            )
            status = Popen(cmd, shell=True).wait()

            if status != 0:
                raise Exception(
                    'Status error raised in %s executing "%s"'
                    % (launch_procs_base.__name__, cmd)
                )

    cmd = (
        "pmt.rb -p "
        + self.pmt_port
        + " -d "
        + self.pmtconfigname
        + " --logpath "
        + self.log_directory
        + " --logfhicl "
        + messagefacility_fhicl_filename
        + " --display $DISPLAY & "
    )

    self.launch_cmds.append(cmd)

    launchcmd = construct_checked_command( self.launch_cmds )

    if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
        launchcmd = "ssh -f " + self.pmt_host + " '" + launchcmd + "'"

    self.print_log("d", "PROCESS LAUNCH COMMANDS: \n" + "\n".join( self.launch_cmds ), 3)

    with deepsuppression(self.debug_level < 5):
        status = Popen(launchcmd, shell=True, preexec_fn=os.setpgrp).wait()

    if status != 0:   
        raise Exception(
            'Status error raised; commands were "\n%s\n\n". For more information, you can check to see if a pmt (process management tool) logfile was produced during the failure in the directory %s/pmt on %s. Also try again with "debug level" set to 4 in the boot file, or even running the above commands interactively on %s after performing a clean login and source-ing the DAQInterface environment.'
            % (
                "\n".join(self.launch_cmds),
                self.log_directory,
                self.pmt_host,
                self.pmt_host,
            )
        )
    return { self.pmt_host : self.launch_cmds }

    
def kill_procs_base(self):

    # JCF, 12/29/14

    # If the PMT host hasn't been defined, we can be sure there
    # aren't yet any artdaq processes running yet (or at least, we
    # won't be able to determine where they're running!)

    if self.pmt_host is None:
        return

    # Now, the commands which will clean up the pmt.rb + its child
    # artdaq processes

    pmt_pids = get_pids("ruby.*pmt.rb -p " + str(self.pmt_port), self.pmt_host)

    if len(pmt_pids) > 0:

        for pmt_pid in pmt_pids:

            cmd = "kill %s; sleep 2; kill -9 %s" % (pmt_pid, pmt_pid)

            if self.pmt_host != "localhost":
                cmd = "ssh -x " + self.pmt_host + " '" + cmd + "'"

            proc = Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

    for procinfo in self.procinfos:

        greptoken = procinfo.name + "Main -c id: " + procinfo.port

        pids = get_pids(greptoken, procinfo.host)

        if len(pids) > 0:
            cmd = "kill -9 " + pids[0]

            if procinfo.host != "localhost":
                cmd = "ssh -x " + procinfo.host + " '" + cmd + "'"

            Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            # Check that it was actually killed

            sleep(1)

            pids = get_pids(greptoken, procinfo.host)

            if len(pids) > 0:
                self.print_log(
                    "w",
                    "Appeared to be unable to kill %s at %s:%s during cleanup"
                    % (procinfo.label, procinfo.host, procinfo.port),
                )

    self.procinfos = []

    return


def mopup_process_base(self, procinfo):
    pass   # Any killing of individual processes would bring down everything else with it when pmt.rb is used


def softlink_process_manager_logfiles_base(self):

    linked_pmt_logfile = False

    greptoken = "pmt.rb -p " + self.pmt_port
    pids = get_pids(greptoken, self.pmt_host)

    for pmt_pid in pids:

        get_pmt_logfile_cmd = "ls -tr %s/pmt/pmt-%s.* | tail -1" % (
            self.log_directory,
            pmt_pid,
        )

        if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
            get_pmt_logfile_cmd = "ssh -f %s '%s'" % (
                self.pmt_host,
                get_pmt_logfile_cmd,
            )

        ls_output = Popen(
            get_pmt_logfile_cmd, shell=True, stdout=subprocess.PIPE
        ).stdout.readlines()

        if len(ls_output) == 1:
            pmt_logfile = ls_output[0].strip()            

            link_pmt_logfile_cmd = "ln -s %s %s/pmt/run%d-pmt.log" % (
                pmt_logfile,
                self.log_directory,
                self.run_number,
            )

            if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
                link_pmt_logfile_cmd = "ssh %s '%s'" % (
                    self.pmt_host,
                    link_pmt_logfile_cmd,
                )

            status = Popen(link_pmt_logfile_cmd, shell=True).wait()

            if status == 0:
                linked_pmt_logfile = True
                break
            else:
                break

    if not linked_pmt_logfile:
        self.print_log("w", "WARNING: failure in attempt to softlink to pmt logfile")


def find_process_manager_variable_base(self, line):

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
    if not hasattr(self, "pmt_port") or self.pmt_port is None:
        self.pmt_port = str( int(self.rpc_port) + 1 )

    undefined_vars = []
    if not hasattr(self, "pmt_host") or self.pmt_host is None:
        undefined_vars.append("PMT host")

    if len(undefined_vars) > 0:
        raise Exception(
            "Error: the following parameters needed by DAQInterface are undefined: %s"
            % (",".join(undefined_vars))
        )


def reset_process_manager_variables_base(self):
    self.pmt_host = None
    self.pmt_port = None


def get_process_manager_log_filenames_base(self):

    cmd = "ls -tr1 %s/pmt | tail -1" % (self.log_directory)

    if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
        cmd = "ssh %s '%s'" % (self.pmt_host, cmd)

    log_filename_current = (
        Popen(cmd, shell=True, stdout=subprocess.PIPE)
        .stdout.readlines()[0]
        .strip()
        .decode("utf-8")
    )

    host = self.pmt_host
    if host == "localhost":
        host = os.environ["HOSTNAME"]
    return [ "%s:%s/pmt/%s" % (host, self.log_directory, log_filename_current) ]


def process_manager_cleanup_base(self):

    if hasattr(self, "pmtconfigname") and os.path.exists(self.pmtconfigname):
        cmd = "rm -f %s" % (self.pmtconfigname)

        if hasattr(self, "pmt_host"):
            if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
                cmd = "ssh -x " + self.pmt_host + " '" + cmd + "'"


def get_pid_for_process_base(self, procinfo):

    assert procinfo in self.procinfos

    greptoken = procinfo.name + "Main -c id: " + procinfo.port

    grepped_lines = []
    pids = get_pids(greptoken, procinfo.host, grepped_lines)

    if len(pids) == 1:    
        return pids[0]
    elif len(pids) == 0:
        return None
    else:
        for grepped_line in grepped_lines:
            print (grepped_line)

        print(
            "Appear to have duplicate processes for %s on %s, pids: %s"
            % (procinfo.label, procinfo.host, " ".join(pids))
        )


# check_proc_heartbeats_base() will check that the expected artdaq
# processes are up and running


def check_proc_heartbeats_base(self, requireSuccess=True):

    is_all_ok = True
    found_processes = []

    for procinfo in self.procinfos:

        if "BoardReader" in procinfo.name:
            proctype = "BoardReaderMain"
        elif "EventBuilder" in procinfo.name:
            proctype = "EventBuilderMain"
        elif "RoutingManager" in procinfo.name:
            proctype = "RoutingManagerMain"
        elif "DataLogger" in procinfo.name:
            proctype = "DataLoggerMain"
        elif "Dispatcher" in procinfo.name:
            proctype = "DispatcherMain"
        else:
            assert False

        if get_pid_for_process_base(self, procinfo) is not None:
            found_processes.append(procinfo)
        else:
            is_all_ok = False

    if not is_all_ok:
        missing_processes = [
            procinfo for procinfo in self.procinfos if procinfo not in found_processes
        ]

    if not is_all_ok and requireSuccess:
        self.heartbeat_failure = True
        pmtlogfiles = self.get_process_manager_log_filenames()
        assert len(pmtlogfiles) == 1
        self.alert_and_recover(
            "Please check process management logfile %s and, if available, the MessageViewer window, as the following artdaq processes appear to have died unexpectedly: %s"
            % (
                self.pmt_host,
                ",".join(
                    [
                        "%s at %s:%s" % (procinfo.label, procinfo.host, procinfo.port)
                        for procinfo in missing_processes
                    ]
                ),
            )
        )
        
    if is_all_ok:
        assert len(found_processes) == len(self.procinfos)

    return found_processes


def process_launch_diagnostics_base(self, procinfos_of_failed_processes):
    pass

def handle_bad_process_base(self, procinfo):

    if self.shepherd_bad_processes == True:
        self.print_log("w", make_paragraph("Warning: shepherd_bad_processes is set to true in the DAQInterface settings file \"%s\", but you're using pmt process management which doesn't support shepherding. No action will be taken on bad process \"%s\"." % (os.environ["DAQINTERFACE_SETTINGS"], procinfo.label)))
    return [pi for pi in self.procinfos if pi.label != procinfo.label]

