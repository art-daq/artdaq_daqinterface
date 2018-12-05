
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
from rc.control.deepsuppression import deepsuppression

# JCF, 8/11/14

# launch_procs_base() will create the artdaq processes

def launch_procs_base(self):

    greptoken = "pmt.rb -p " + self.pmt_port
    pids = get_pids(greptoken, self.pmt_host)

    if len(pids) != 0:
        raise Exception("\"pmt.rb -p %s\" was already running on %s" %
                        (self.pmt_port, self.pmt_host))

    self.print_log("d",  "Assuming daq package is in " + \
                   self.daq_dir, 2)

    # We'll use the desired features of the artdaq processes to
    # create a text file which will be passed to artdaq's pmt.rb
    # program

    self.pmtconfigname = "/tmp/pmtConfig." + \
        ''.join(random.choice(string.digits)
                for _ in range(5))

    outf = open(self.pmtconfigname, "w")

    # The rank MPI assigns the artdaq process corresponds to the order it appears in the pmtConfig file below

    for procinfo in sorted( self.procinfos, key=lambda procinfo: int(procinfo.rank) ) :
        outf.write(procinfo.name + "Main!")

        if procinfo.host != "localhost":
            host_to_write = procinfo.host
        else:
            host_to_write = os.environ["HOSTNAME"]

        outf.write(host_to_write + "!  id: " + procinfo.port + " commanderPluginType: xmlrpc application_name: " + str(procinfo.label) + " partition_number: " + str(self.partition_number) + "\n")

    outf.close()

    if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
        status = Popen("scp -p " + self.pmtconfigname + " " +
                       self.pmt_host + ":/tmp", shell=True).wait()

        if status != 0:
            raise Exception("Exception in DAQInterface: unable to copy " +
                            self.pmtconfigname + " to " + self.pmt_host + ":/tmp")

    self.launch_cmds = []

    for logdir in ["pmt", "boardreader", "eventbuilder",
                   "dispatcher", "datalogger", "routingmaster"]:
        if not os.path.exists( "%s/%s" % (self.log_directory, logdir)):
            self.launch_cmds.append("mkdir -p -m 0777 " + "%s/%s" % (self.log_directory, logdir) )

    self.launch_cmds.append(". %s/setup" % self.productsdir)  
    self.launch_cmds.append( bash_unsetup_command )
    self.launch_cmds.append("source " + self.daq_setup_script )
    self.launch_cmds.append("which pmt.rb")  # Sanity check capable of returning nonzero

    # 30-Jan-2017, KAB: increased the amount of time that pmt.rb provides daqinterface
    # to react to errors.  This should be longer than the sum of the individual
    # process timeouts.
    self.launch_cmds.append("export ARTDAQ_PROCESS_FAILURE_EXIT_DELAY=120")

    if self.have_artdaq_mfextensions():

        write_new_file = True

        if "DAQINTERFACE_MESSAGEFACILITY_FHICL" in os.environ.keys():
            messagefacility_fhicl_filename = os.environ["DAQINTERFACE_MESSAGEFACILITY_FHICL"]
        else:
            messagefacility_fhicl_filename = os.getcwd() + "/MessageFacility.fcl" 

        # JCF, 10-25-2018

        # The FHiCL controlling messagefacility messages below is
        # embedded by artdaq within other FHiCL code (see
        # artdaq/DAQdata/configureMessageFacility.cc in artdaq
        # v2_03_03 for details).

        default_contents = """ 

# This file was automatically generated as %s at %s on host %s, and is
# the default file DAQInterface uses to determine how to modify the
# standard MessageFacility configuration found in artdaq-core
# v3_02_01's configureMessageFacility.cc file. You can edit the
# contents below to change the behavior of how/where MessageFacility
# messages are sent, though keep in mind that this FHiCL will be
# nested inside a table. Or you can use a different file by setting
# the environment variable DAQINTERFACE_MESSAGEFACILITY_FHICL to the
# name of the other file.

udp : { type : "UDP" threshold : "DEBUG"  port : 30000 host : "%s" } 

""" % (messagefacility_fhicl_filename, date_and_time(), os.environ["HOSTNAME"], socket.gethostname())
        

        if not os.path.exists( messagefacility_fhicl_filename ):
            with open(messagefacility_fhicl_filename, "w") as outf_mf:
                outf_mf.write( default_contents )

        cmd = "pmt.rb -p " + self.pmt_port + " -d " + self.pmtconfigname + \
            " --logpath " + self.log_directory + \
            " --logfhicl " + messagefacility_fhicl_filename + " --display $DISPLAY & "
    else:

        cmd = "pmt.rb -p " + self.pmt_port + " -d " + self.pmtconfigname + \
            " --logpath " + self.log_directory + \
            " --display $DISPLAY & "

    self.launch_cmds.append(cmd)

    launchcmd = construct_checked_command( self.launch_cmds )

    if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
        launchcmd = "ssh -f " + self.pmt_host + " '" + launchcmd + "'"

    self.print_log("d", "PROCESS LAUNCH COMMANDS: \n" + "\n".join( self.launch_cmds ), 2)

    with deepsuppression(self.debug_level < 4):
        status = Popen(launchcmd, shell=True).wait()

    if status != 0:   
        raise Exception("Status error raised; commands were \"\n%s\n\n\". If logfiles exist, please check them for more information. Also try running the commands interactively in a new terminal (after source-ing the DAQInterface environment) for more info." %
                        ("\n".join(self.launch_cmds)))
        return


def kill_procs_base(self):

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

    linked_pmt_logfile = False

    greptoken = "pmt.rb -p " + self.pmt_port
    pids = get_pids(greptoken, self.pmt_host)

    for pmt_pid in pids:

        get_pmt_logfile_cmd = "ls -tr %s/pmt/pmt-%s.* | tail -1" % \
                              (self.log_directory, pmt_pid)

        if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
            get_pmt_logfile_cmd = "ssh -f %s '%s'" % (self.pmt_host, get_pmt_logfile_cmd)

        ls_output = Popen(get_pmt_logfile_cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()

        if len(ls_output) == 1:
            pmt_logfile = ls_output[0].strip()            

            link_pmt_logfile_cmd = "ln -s %s %s/pmt/run%d-pmt.log" % \
                                   (pmt_logfile, self.log_directory, self.run_number)

            if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
                link_pmt_logfile_cmd = "ssh %s '%s'" % (self.pmt_host, link_pmt_logfile_cmd)

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
        raise Exception("Error: the following parameters needed by DAQInterface are undefined: %s" % \
                        ( ",".join( undefined_vars ) ))

def get_process_manager_log_filenames_base(self):

    cmd = "ls -tr1 %s/pmt | tail -1" % (self.log_directory)

    if self.pmt_host != "localhost" and self.pmt_host != os.environ["HOSTNAME"]:
        cmd = "ssh %s '%s'" % (self.pmt_host, cmd)

    log_filename_current = Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip()

    host = self.pmt_host
    if host == "localhost":
        host = os.environ["HOSTNAME"]
    return [ "%s:%s/pmt/%s" % (host, self.log_directory, log_filename_current) ]


                        

