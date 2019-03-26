#!/bin/env python

import os
import sys
sys.path.append( os.environ["ARTDAQ_DAQINTERFACE_DIR"] )

import argparse
import datetime
import subprocess
from subprocess import Popen
from time import sleep, time
import traceback
import re
import string
import glob
import stat
from threading import Thread
import shutil
import random

from rc.io.timeoutclient import TimeoutServerProxy
from rc.control.component import Component 
from rc.control.deepsuppression import deepsuppression

from rc.control.save_run_record import save_run_record_base
from rc.control.save_run_record import total_events_in_run_base
from rc.control.save_run_record import save_metadata_value_base
from rc.control.all_functions_noop import start_datataking_base
from rc.control.all_functions_noop import stop_datataking_base
from rc.control.all_functions_noop import do_enable_base
from rc.control.all_functions_noop import do_disable_base
from rc.control.bookkeeping import bookkeeping_for_fhicl_documents_artdaq_v3_base

from rc.control.online_monitoring import launch_art_procs_base
from rc.control.online_monitoring import kill_art_procs_base

from rc.control.utilities import expand_environment_variable_in_string
from rc.control.utilities import make_paragraph
from rc.control.utilities import get_pids
from rc.control.utilities import is_msgviewer_running
from rc.control.utilities import date_and_time
from rc.control.utilities import construct_checked_command
from rc.control.utilities import reformat_fhicl_documents
from rc.control.utilities import fhicl_writes_root_file
from rc.control.utilities import bash_unsetup_command

if not "DAQINTERFACE_PROCESS_MANAGEMENT_METHOD" in os.environ:
    print
    raise Exception(make_paragraph("The DAQINTERFACE_PROCESS_MANAGEMENT_METHOD environment variable must be defined; legal values include \"pmt\" and \"direct\""))

elif os.environ["DAQINTERFACE_PROCESS_MANAGEMENT_METHOD"] == "pmt":
    from rc.control.manage_processes_pmt import launch_procs_base
    from rc.control.manage_processes_pmt import kill_procs_base
    from rc.control.manage_processes_pmt import check_proc_heartbeats_base
    from rc.control.manage_processes_pmt import softlink_process_manager_logfiles_base
    from rc.control.manage_processes_pmt import find_process_manager_variable_base
    from rc.control.manage_processes_pmt import set_process_manager_default_variables_base
    from rc.control.manage_processes_pmt import reset_process_manager_variables_base
    from rc.control.manage_processes_pmt import get_process_manager_log_filenames_base
    from rc.control.manage_processes_pmt import process_manager_cleanup_base
    from rc.control.manage_processes_pmt import get_pid_for_process_base
    from rc.control.manage_processes_pmt import process_launch_diagnostics_base
    from rc.control.manage_processes_pmt import mopup_process_base
elif os.environ["DAQINTERFACE_PROCESS_MANAGEMENT_METHOD"] == "direct":
    from rc.control.manage_processes_direct import launch_procs_base
    from rc.control.manage_processes_direct import kill_procs_base
    from rc.control.manage_processes_direct import check_proc_heartbeats_base
    from rc.control.manage_processes_direct import softlink_process_manager_logfiles_base
    from rc.control.manage_processes_direct import find_process_manager_variable_base
    from rc.control.manage_processes_direct import set_process_manager_default_variables_base
    from rc.control.manage_processes_direct import reset_process_manager_variables_base
    from rc.control.manage_processes_direct import get_process_manager_log_filenames_base
    from rc.control.manage_processes_direct import process_manager_cleanup_base
    from rc.control.manage_processes_direct import get_pid_for_process_base
    from rc.control.manage_processes_direct import process_launch_diagnostics_base
    from rc.control.manage_processes_direct import mopup_process_base
else:
    print
    raise Exception(make_paragraph("DAQInterface can't interpret the current value of the DAQINTERFACE_PROCESS_MANAGEMENT_METHOD environment variable (\"%s\"); legal values include \"pmt\" and \"direct\"" % os.environ["DAQINTERFACE_PROCESS_MANAGEMENT_METHOD"]))


if not "DAQINTERFACE_FHICL_DIRECTORY" in os.environ:
    print
    raise Exception(make_paragraph("The DAQINTERFACE_FHICL_DIRECTORY environment variable must be defined; if you wish to use the database rather than the local filesystem for FHiCL document retrieval, set DAQINTERFACE_FHICL_DIRECTORY to IGNORED"))
elif os.environ["DAQINTERFACE_FHICL_DIRECTORY"] == "IGNORED":
    from rc.control.config_functions_database_v2 import get_config_info_base
    from rc.control.config_functions_database_v2 import put_config_info_base
    from rc.control.config_functions_database_v2 import listconfigs_base

else:
    from rc.control.config_functions_local import get_config_info_base
    from rc.control.config_functions_local import put_config_info_base
    from rc.control.config_functions_local import listconfigs_base

from rc.control.config_functions_local import get_boot_info_base
from rc.control.config_functions_local import listdaqcomps_base


class DAQInterface(Component):
    """
    DAQInterface: The intermediary between Run Control, the
    configuration database, and artdaq processes

    """

    # "Procinfo" is basically just a simple structure containing all
    # the info about a given artdaq process that DAQInterface might
    # care about

    # However, it also contains a less-than function which allows it
    # to be sorted s.t. processes you'd want shutdown first appear
    # before processes you'd want shutdown last (in order:
    # boardreader, eventbuilder, datalogger, dispatcher, routingmaster)

    # JCF, Nov-17-2015

    # I add the "fhicl_file_path" variable, which is a sequence of
    # paths which are searched in order to cut-and-paste #include'd
    # files (see also the description of the DAQInterface class's
    # fhicl_file_path variable, whose sole purpose is to be passed to
    # Procinfo's functions)

    # JCF, Apr-26-2018
    
    # The "label" variable is used to pick out specific FHiCL files
    # for EventBuilders, DataLoggers, Dispatchers and RoutingMasters;
    # a given process's label is set in the boot file, alongside its
    # host and port

    class Procinfo(object):
        def __init__(self, name, rank, host, port, label=None, subsystem="1", fhicl=None, fhicl_file_path = []):
            self.name = name
            self.rank = rank
            self.port = port
            self.host = host
            self.label = label
            self.subsystem = subsystem
            self.fhicl = fhicl     # Name of the input FHiCL document
            self.ffp = fhicl_file_path
            self.priority = 999

            # FHiCL code actually sent to the process

            # JCF, 11/11/14 -- note that "fhicl_used" will be modified
            # during the initalization function, as bookkeeping, etc.,
            # is performed on FHiCL parameters

            if self.fhicl is not None:
                self.fhicl_used = ""
                self.recursive_include(self.fhicl)
            else:
                self.fhicl_used = None

            # JCF, Jan-14-2016

            # Do NOT change the "lastreturned" string below without
            # changing the commensurate string in check_proc_transition!

            self.lastreturned = "DAQInterface: ARTDAQ PROCESS NOT YET CALLED"
            self.socketstring = "http://" + self.host + ":" + self.port \
                + "/RPC2"

        def update_fhicl(self, fhicl):
            self.fhicl = fhicl
            self.fhicl_used = ""
            self.recursive_include(self.fhicl)

        def __lt__(self, other):
            if self.name != other.name:

                processes_upstream_to_downstream = \
                    ["BoardReader", "EventBuilder", "DataLogger", "Dispatcher", "RoutingMaster"]

                if processes_upstream_to_downstream.index(self.name) < \
                        processes_upstream_to_downstream.index(other.name):
                    return True
                else:
                    return False
            else:
                if int(self.port) < int(other.port):
                    return True
                return False

        def recursive_include(self, filename):

            if self.fhicl is not None:            
                for line in open(filename).readlines():

                    if "#include" not in line:
                        self.fhicl_used += line
                    else:
                        res = re.search(r"^\s*#.*#include", line)

                        if res:
                            self.fhicl_used += line
                            continue

                        res = re.search(r"^\s*#include\s+\"(\S+)\"", line)
                        
                        if not res:
                            raise Exception(make_paragraph("Error in Procinfo::recursive_include: "
                                            "unable to parse line \"%s\" in %s" %
                                            (line, filename)))

                        included_file = res.group(1)

                        if included_file[0] == "/":
                            if not os.path.exists(included_file):
                                raise Exception(make_paragraph("Error in "
                                                                    "Procinfo::recursive_include: "
                                                                    "unable to find file %s included in %s" %
                                                               (included_file, filename)))
                            else:
                                self.recursive_include(included_file)
                        else:
                            found_file = False
                            
                            for dirname in self.ffp:
                                if os.path.exists( dirname + "/" + included_file) and not found_file:
                                    self.recursive_include(dirname + "/" + included_file)
                                    found_file = True

                            if not found_file:
                                
                                ffp_string = ":".join(self.ffp)

                                raise Exception(make_paragraph(
                                        "Error in Procinfo::recursive_include: "
                                        "unable to find file %s in list of "
                                        "the following fhicl_file_paths: %s" %
                                        (included_file, ffp_string)))

    # "Subsystem" is a structure containing all the info about a given
    # artdaq subsytem.

    class Subsystem(object):
        def __init__(self, source = None, destination = None):
            self.source = source
            self.destination = destination

        def __lt__(self, other):
            if self.id != other.id:

                if self.destination == other.id:
                    return True
                else:
                    return False
            else:
                return False # equal

    def print_log(self, severity, printstr, debuglevel=-999, newline=True):

        dummy, month, day, time, timezone, year = date_and_time().split()
        formatted_day = "%s-%s-%s" % (day, month, year)

        if self.debug_level >= debuglevel:
            if self.fake_messagefacility:
                print "%%MSG-%s DAQInterface %s %s %s" % \
                    (severity, formatted_day, time, timezone)
            if not newline and not self.fake_messagefacility:
                sys.stdout.write(printstr)
                sys.stdout.flush()
            else:
                print printstr
            if self.fake_messagefacility:
                print "%MSG"

    # JCF, Dec-16-2016

    # The purpose of reset_variables is to reset those members that
    # (A) aren't necessarily persistent to the process (thus excluding
    # the parameters in $DAQINTERFACE_SETTINGS) and (B) won't
    # necessarily be set explicitly during the transitions up from the
    # "stopped" state. E.g., you wouldn't want to return to the
    # "stopped" state with self.exception == True and then try a
    # boot-config-start without self.exception being reset to False

    def reset_variables(self):

        self.exception = False
        self.in_recovery = False
        self.heartbeat_failure = False
        self.manage_processes = True
        self.disable_recovery = False

        self.reset_process_manager_variables()

        # "procinfos" will be an array of Procinfo structures (defined
        # above), where Procinfo contains all the info DAQInterface
        # needs to know about an individual artdaq process: name,
        # host, port, and FHiCL initialization document. Filled
        # through a combination of info in the DAQInterface
        # configuration file as well as the components list

        self.procinfos = []


        # "subsystems" is an dictionary of Subsystem structures (defined above),
        # where Subsystem contains all the information DAQInterface needs
        # to know about artdaq subsystems: id (dictionary key), source subsystem, destination subsystem.
        # Subsystems are an optional feature that allow users to build complex configurations
        # with multiple request domains and levels of filtering.
        self.subsystems = {}

    # Constructor for DAQInterface begins here

    def __init__(self, logpath=None, name="toycomponent",
                 rpc_host="localhost", control_host='localhost',
                 synchronous=True, rpc_port=6659, partition_number=999):

        # Initialize Component, the base class of DAQInterface

        Component.__init__(self, logpath=logpath,
                           name=name,
                           rpc_host=rpc_host,
                           control_host=control_host,
                           synchronous=synchronous,
                           rpc_port=rpc_port,
                           skip_init=False)

        self.manage_processes = True
        self.disable_recovery = False

        self.in_recovery = False
        self.heartbeat_failure = False
        self.called_launch_procs = False

        self.debug_level = 10000
        self.request_address = None
        self.request_port = None 
        self.table_update_address = None
        self.routing_base_port = None
        self.partition_number = partition_number
        self.transfer = "Autodetect"
        self.rpc_port = rpc_port

        self.daqinterface_base_dir = os.getcwd()
            
        # JCF, Nov-17-2015

        # fhicl_file_path is a sequence of directory names which will
        # be searched for any FHiCL documents #include'd by the main
        # document used to initialize each artdaq process, but not
        # given with an absolute path in the #include .

        self.fhicl_file_path = []

        # JCF, Jan-31-2019

        # Labels of processes which, if they die or enter an Error state, will result in the run ending. 

        self.critical_processes_list = []  

        # JCF, Nov-7-2015

        # Now that we're going with a multithreaded (simultaneous)
        # approach to sending transition commands to artdaq processes,
        # when an exception is thrown a thread the main thread needs
        # to know about it somehow - thus this new exception variable

        self.exception = False

        self.check_proc_exceptions_number_of_status_failures = 0

        self.__do_boot = False
        self.__do_shutdown = False
        self.__do_config = False
        self.__do_start_running = False
        self.__do_stop_running = False
        self.__do_terminate = False
        self.__do_pause_running = False
        self.__do_resume_running = False
        self.__do_recover = False
        self.__do_enable = False
        self.__do_disable = False

        try:
            self.read_settings()
        except:
            self.print_log("e", traceback.format_exc())
            self.print_log("e", make_paragraph(
                    "An exception was thrown when trying to read DAQInterface settings; "
                    "DAQInterface will exit. Look at the messages above, make any necessary "
                    "changes, and restart.") + "\n")
            sys.exit(1)

        if "DAQINTERFACE_CRITICAL_PROCESSES_LIST" in os.environ:
            self.critical_processes_list = []
            if not os.path.exists(os.environ["DAQINTERFACE_CRITICAL_PROCESSES_LIST"]):
                raise Exception("Environment variable DAQINTERFACE_CRITICAL_PROCESSES_LIST is set to \"%s\" but the file doesn't appear to exist" % (os.environ["DAQINTERFACE_CRITICAL_PROCESSES_LIST"]))

            with open(os.environ["DAQINTERFACE_CRITICAL_PROCESSES_LIST"]) as inf:
                for line in inf.readlines():
                    if not re.search(r"^\s*$", line) and not re.search(r"^\s*#", line):
                        self.critical_processes_list.append(line.split()[0])
                    else:
                        continue

        self.print_log("i", "DAQInterface in partition %s launched and now in \"%s\" state, listening on port %d" % 
                                           (self.partition_number, self.state(self.name), self.rpc_port))

    get_config_info = get_config_info_base
    put_config_info = put_config_info_base
    get_boot_info = get_boot_info_base
    listdaqcomps = listdaqcomps_base
    listconfigs = listconfigs_base
    save_run_record = save_run_record_base
    total_events_in_run = total_events_in_run_base
    save_metadata_value = save_metadata_value_base
    start_datataking = start_datataking_base
    stop_datataking = stop_datataking_base
    bookkeeping_for_fhicl_documents = bookkeeping_for_fhicl_documents_artdaq_v3_base
    launch_art_procs = launch_art_procs_base
    kill_art_procs = kill_art_procs_base
    do_enable = do_enable_base
    do_disable = do_disable_base
    launch_procs = launch_procs_base
    kill_procs = kill_procs_base
    check_proc_heartbeats = check_proc_heartbeats_base
    softlink_process_manager_logfiles = softlink_process_manager_logfiles_base
    find_process_manager_variable = find_process_manager_variable_base
    set_process_manager_default_variables = set_process_manager_default_variables_base
    reset_process_manager_variables = reset_process_manager_variables_base
    get_process_manager_log_filenames = get_process_manager_log_filenames_base
    process_manager_cleanup = process_manager_cleanup_base
    process_launch_diagnostics = process_launch_diagnostics_base
    mopup_process = mopup_process_base
    get_pid_for_process = get_pid_for_process_base

    # The actual transition functions called by Run Control; note
    # these just set booleans which are tested in the runner()
    # function, called periodically by run control

    def boot(self):
        self.__do_boot = True

    def shutdown(self):
        self.__do_shutdown = True

    def config(self):
        self.__do_config = True

    def recover(self):
        self.__do_recover = True

    def start_running(self):
        self.__do_start_running = True

    def stop_running(self):
        self.__do_stop_running = True

    def terminate(self):
        self.__do_terminate = True

    def pause_running(self):
        self.__do_pause_running = True

    def resume_running(self):
        self.__do_resume_running = True

    def enable(self):
        self.__do_enable = True

    def disable(self):
        self.__do_disable = True

    def alert_and_recover(self, extrainfo=None):

        self.do_recover()
                
        alertmsg = ""
        
        if not extrainfo is None:
            alertmsg = "\n\n" + make_paragraph( "\"" + extrainfo + "\"")

        alertmsg += "\n" + make_paragraph("DAQInterface has set the DAQ back in the \"Stopped\" state; you may need to scroll above the Recover transition output to find messages which could help you provide any necessary adjustments.")
        self.print_log("e",  alertmsg )
        print

    def read_settings(self):
        if not os.path.exists( os.environ["DAQINTERFACE_SETTINGS"]):
            raise Exception(make_paragraph("Unable to find settings file \"%s\"" % \
                                           os.environ["DAQINTERFACE_SETTINGS"]))

        inf = open( os.environ["DAQINTERFACE_SETTINGS"] )
        assert inf

        self.log_directory = None
        self.record_directory = None
        self.daq_setup_script = None
        self.package_hashes_to_save = []
        self.productsdir_for_bash_scripts = None
        self.max_fragment_size_bytes = None

        self.boardreader_timeout = 30
        self.eventbuilder_timeout = 30
        self.datalogger_timeout = 30
        self.dispatcher_timeout = 30
        self.routingmaster_timeout = 30

        self.use_messageviewer = True
        self.advanced_memory_usage = False
        self.fake_messagefacility = False
        self.data_directory_override = None
        self.max_configurations_to_list = 1000000
        self.disable_unique_rootfile_labels = True

        self.productsdir = None

        for line in inf.readlines():

            line = expand_environment_variable_in_string( line )

            # Allow same-line comments
            res = re.search(r"^(.*)#.*", line)
            if res:
                line = res.group(1)

            line = line.strip()

            if re.search(r"^\s*#", line):
                continue
            elif "log_directory" in line or "log directory" in line:
                self.log_directory = line.split()[-1].strip()
            elif "record_directory" in line or "record directory" in line:
                self.record_directory = line.split()[-1].strip()
            elif "productsdir_for_bash_scripts" in line or "productsdir for bash scripts" in line:
                self.productsdir = line.split()[-1].strip()
            elif "package_hashes_to_save" in line or "package hashes to save" in line:
                res = re.search(r".*\[(.*)\].*", line)

                if not res:
                    raise Exception(make_paragraph(
                            "Unable to parse package_hashes_to_save line in the settings file, %s" % \
                                (os.environ["DAQINTERFACE_SETTINGS"])))

                if res.group(1).strip() == "":
                    continue

                package_hashes_to_save_unprocessed = res.group(1).split(",")

                for ip, package in enumerate(package_hashes_to_save_unprocessed):
                    package = string.replace(package, "\"", "")
                    package = string.replace(package, " ", "") # strip() doesn't seem to work here
                    self.package_hashes_to_save.append(package)
            elif "boardreader_timeout" in line or "boardreader timeout" in line:
                self.boardreader_timeout = int( line.split()[-1].strip() )
            elif "eventbuilder_timeout" in line or "eventbuilder timeout" in line:
                self.eventbuilder_timeout = int( line.split()[-1].strip() )
            elif "datalogger_timeout" in line or "datalogger timeout" in line:
                self.datalogger_timeout = int( line.split()[-1].strip() )
            elif "dispatcher_timeout" in line or "dispatcher timeout" in line:
                self.dispatcher_timeout = int( line.split()[-1].strip() )
            elif "boardreader_priorities" in line or "boardreader priorities" in line:
                self.boardreader_priorities = [regexp.strip() for regexp in line.split()[2:] if ":" not in regexp]
            elif "max_fragment_size_bytes" in line or "max fragment size bytes" in line:
                max_fragment_size_bytes_token = line.split()[-1].strip()

                if max_fragment_size_bytes_token[0:2] != "0x":
                    self.max_fragment_size_bytes = int( max_fragment_size_bytes_token )
                else:
                    self.max_fragment_size_bytes = int( max_fragment_size_bytes_token[2:], 16)

                if self.max_fragment_size_bytes % 8 != 0:
                    raise Exception("Value for \"max_fragment_size_bytes\" in settings file \"%s\" should be a multiple of 8" % (os.environ["DAQINTERFACE_SETTINGS"]))
            elif "max_configurations_to_list" in line or "max configurations to list" in line:
                self.max_configurations_to_list = int( line.split()[-1].strip() )
            elif "disable_unique_rootfile_labels" in line or "disable unique rootfile labels" in line:
                token = line.split()[-1].strip()
                if "true" in token or "True" in token:
                    self.disable_unique_rootfile_labels = True
                elif "false" in token or "False" in token:
                    self.disable_unique_rootfile_labels = False
                else:
                    raise Exception("disable_unique_rootfile_labels must be set to either [Tt]rue or [Ff]alse")
            elif "use_messageviewer" in line or "use messageviewer" in line:
                token = line.split()[-1].strip()
                
                res = re.search(r"[Ff]alse", token)

                if res:
                    self.use_messageviewer = False
            elif "advanced_memory_usage" in line or "advanced memory usage" in line:
                token = line.split()[-1].strip()
                
                res = re.search(r"[Tt]rue", token)

                if res:
                    self.advanced_memory_usage = True
            elif "fake_messagefacility" in line or "fake messagefacility" in line:
                token = line.split()[-1].strip()
                
                res = re.search(r"[Tt]rue", token)

                if res:
                    self.fake_messagefacility = True
            elif "data_directory_override" in line or "data directory override" in line:
                self.data_directory_override = line.split()[-1].strip()
                if self.data_directory_override[-1] != "/":
                    self.data_directory_override = self.data_directory_override + "/"
            elif "transfer_plugin_to_use" in line or "transfer plugin to use" in line:
                self.transfer = line.split()[-1].strip()
                

        missing_vars = []

        if self.log_directory is None:
            missing_vars.append("log_directory")
            
        if self.record_directory is None:
            missing_vars.append("record_directory")

        if self.productsdir is None:
            missing_vars.append("productsdir_for_bash_scripts")

        if not self.advanced_memory_usage and self.max_fragment_size_bytes is None:
            missing_vars.append("max_fragment_size_bytes")

        if self.advanced_memory_usage and self.max_fragment_size_bytes is not None:
            raise Exception(make_paragraph("Since advanced_memory_usage is set to true in the settings file (%s), max_fragment_size_bytes must NOT be set (i.e., delete it or comment it out)" % (os.environ["DAQINTERFACE_SETTINGS"])))

        if len(missing_vars) > 0:
            missing_vars_string = ", ".join(missing_vars)
            print
            raise Exception(make_paragraph(
                                "Unable to parse the following variable(s) meant to be set in the "
                                "settings file, %s" % \
                                    (os.environ["DAQINTERFACE_SETTINGS"] + ": " + missing_vars_string ) ))

        if not self.advanced_memory_usage and not self.max_fragment_size_bytes:
            raise Exception(make_paragraph("max_fragment_size_bytes isn't set in the settings file, "
                                           "%s; this needs to be set since advanced_memory_usage isn't set to true" %
                                           os.environ["DAQINTERFACE_SETTINGS"]))
        
                    

    def check_proc_transition(self, target_state):

        is_all_ok = True
        
        # The following code will give artdaq processes max_retries
        # chances to return "Success", if, rather than
        # procinfo.lastreturned indicating an error condition, it
        # simply appears that it hasn't been assigned its new status
        # yet

        for procinfo in self.procinfos:

            if procinfo.lastreturned != "Success" and procinfo.lastreturned != target_state:

                redeemed=False
                max_retries=20
                retry_counter=0
                
                while retry_counter < max_retries and ( 
                    "ARTDAQ PROCESS NOT YET CALLED" in procinfo.lastreturned or
                    "Stopped" in procinfo.lastreturned or
                    "Booted" in procinfo.lastreturned or
                    "Ready" in procinfo.lastreturned or
                    "Running" in procinfo.lastreturned or
                    "Paused" in procinfo.lastreturned or
                    "busy" in procinfo.lastreturned):
                    retry_counter += 1
                    sleep(1)
                    if procinfo.lastreturned  == "Success" or procinfo.lastreturned == target_state:
                        redeemed=True

                if redeemed:
                    successmsg = "After " + str(retry_counter) + " checks, process " + \
                        procinfo.label + " at " + procinfo.host + ":" + procinfo.port + " returned \"Success\""
                    self.print_log("i",  successmsg )
                    continue  # We're fine, continue on to the next process check

                errmsg = "Unexpected status message from process " + procinfo.label + " at " + procinfo.host + \
                    ":" + procinfo.port + ": \"" + \
                    procinfo.lastreturned + "\""
                self.print_log("w", make_paragraph(errmsg))
                print
                self.print_log("w", "See logfile %s for details" % (self.determine_logfilename(procinfo)))

                if "BoardReader" in procinfo.name and target_state == "Ready" and "with ParameterSet" in procinfo.lastreturned:
                    print
                    self.print_log("w", make_paragraph("This is likely because the fragment generator constructor in %s threw an exception (see logfile %s for details)." % (procinfo.label, self.determine_logfilename(procinfo))))

                is_all_ok = False

        if not is_all_ok:
            raise Exception("At least one artdaq process failed a transition")



    # Utility functions used to count the different process types

    def num_boardreaders(self):
        num_boardreaders = 0
        for procinfo in self.procinfos:
            if "BoardReader" in procinfo.name:
                num_boardreaders += 1
        return num_boardreaders

    def num_eventbuilders(self):
        num_eventbuilders = 0
        for procinfo in self.procinfos:
            if "EventBuilder" in procinfo.name:
                num_eventbuilders += 1
        return num_eventbuilders

    def num_dataloggers(self):
        num_dataloggers = 0
        for procinfo in self.procinfos:
            if "DataLogger" in procinfo.name:
                num_dataloggers += 1
        return num_dataloggers

    def have_artdaq_mfextensions(self):

        cmds = []
        cmds.append(bash_unsetup_command)
        cmds.append(". %s" % (self.daq_setup_script))
        cmds.append('if test -n "$SETUP_ARTDAQ_MFEXTENSIONS" -o -d "$ARTDAQ_MFEXTENSIONS_DIR"; then true; else false; fi')

        checked_cmd = construct_checked_command( cmds )
        
        with deepsuppression(self.debug_level < 3):
            status = Popen(checked_cmd, shell = True).wait()

        if status == 0:
            return True
        else:
            return False

    def artdaq_mfextensions_info(self):

        assert self.have_artdaq_mfextensions()

        cmds = []
        cmds.append(bash_unsetup_command)
        cmds.append(". %s" % (self.daq_setup_script))
        cmds.append('if [ -n "$SETUP_ARTDAQ_MFEXTENSIONS" ]; then printenv SETUP_ARTDAQ_MFEXTENSIONS; else echo "artdaq_mfextensions $ARTDAQ_MFEXTENSIONS_VERSION $MRB_QUALS";fi')

        proc = Popen(";".join(cmds), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        proclines = proc.stdout.readlines()

        printenv_line = proclines[-1]
        version = printenv_line.split()[1]
        qualifiers = printenv_line.split()[-1]

        return (version, qualifiers)
    
    # JCF, 5/29/15

    # check_proc_exceptions() takes advantage of an artdaq feature
    # developed by Kurt earlier this month whereby if something goes
    # wrong in an artdaq process during running (e.g., a fragment
    # generator's getNext_() function throws an exception) then, when
    # queried, the artdaq process can return an "Error" state, as
    # opposed to the usual DAQ states ("Ready", "Running", etc.)

    # Feb-26-2017

    # Note that "exceptions" in the context of the function name
    # check_proc_exceptions() refers to an exception being thrown
    # within a fragment generator, resulting in the artdaq process
    # returning an "Error" when queried. It's not the same thing as
    # what the self.exception variable denotes, which is that a
    # literal Python exception got thrown at some point.

    def check_proc_exceptions(self):

        if self.exception:
            return

        for procinfo in self.procinfos:

            try:
                procinfo.lastreturned = procinfo.server.daq.status()
            except Exception:
                self.check_proc_exceptions_number_of_status_failures += 1
                
                if self.check_proc_exceptions_number_of_status_failures >= 2:
                    self.exception = True

                exceptstring = make_paragraph("Exception caught in DAQInterface attempt to query status of artdaq process %s at %s:%s; most likely reason is process no longer exists" % \
                    (procinfo.label, procinfo.host, procinfo.port))              
                self.print_log("e", exceptstring)
                continue

            if procinfo.lastreturned == "Error":

                errmsg = "%s: \"Error\" state found to have been returned by process %s at %s:%s; please check MessageViewer if up and/or the process logfile, %s" % \
                         (date_and_time(), procinfo.label, procinfo.host, procinfo.port, self.determine_logfilename(procinfo) )

                print
                self.print_log("e", make_paragraph(errmsg))
                self.print_log("i", "\nWill remove %s from the list of processes" % (procinfo.label))
                print
                self.mopup_process(procinfo)
                self.procinfos.remove( procinfo )
                print

                if procinfo.label in self.critical_processes_list:
                    self.print_log("e", make_paragraph("Process \"%s\" which returned Error state is in the critical process list (%s); will now end the run and go to the Stopped state" % (procinfo.label, os.environ["DAQINTERFACE_CRITICAL_PROCESSES_LIST"] )))
                    raise Exception("\nCritical process \"%s\" was found in the Error state" % (procinfo.label))

                self.print_log("i", "Processes remaining:\n%s" % ("\n".join( [procinfo.label for procinfo in self.procinfos])))

    def determine_logfilename(self, procinfo):
        loglists = [ self.boardreader_log_filenames, self.eventbuilder_log_filenames, self.datalogger_log_filenames, \
                     self.dispatcher_log_filenames, self.routingmaster_log_filenames ]
        logfilename_in_list_form = [ logfilename for loglist in loglists for logfilename in loglist if "/%s-" % (procinfo.label) in logfilename ]
        assert len(logfilename_in_list_form) == 1, "Incorrect assumption made by DAQInterface about the format of the logfilenames; please contact John Freeman at jcfree@fnal.gov"
        return logfilename_in_list_form[0]

    def check_boot_info(self):

        # Check that the boot file actually contained the
        # definitions we wanted

        # The BoardReader info should be supplied by the configuration
        # manager; info for the other artdaq process types (excluding
        # their FHiCL documents) should be supplied in the
        # boot file

        undefined_var = ""

        if self.daq_setup_script is None:
            undefined_var = "DAQ setup script"
        elif self.debug_level is None:
            undefined_var = "debug level"

        if undefined_var != "":
            errmsg = "Error: \"%s\" undefined in " \
                "DAQInterface config file" % \
                (undefined_var)
            raise Exception(make_paragraph(errmsg))

        if not os.path.exists(self.daq_setup_script ):
            raise Exception(self.daq_setup_script + " script not found")

        num_requested_routingmasters = len( [ procinfo.name for procinfo in self.procinfos 
                                              if procinfo.name == "RoutingMaster" ]  )
        if num_requested_routingmasters > len(self.subsystems):
            raise Exception(make_paragraph("%d RoutingMaster processes defined in the boot file provided; you can't have more than the number of subsystems (%d)" % (num_requested_routingmasters, len(self.subsystems))))

        if len(set([procinfo.label for procinfo in self.procinfos])) < len(self.procinfos):
            raise Exception(make_paragraph("At least one of your desired artdaq processes has a duplicate label; please check the boot file to ensure that each process gets a unique label"))

    def get_artdaq_log_filenames(self):

        self.boardreader_log_filenames = []
        self.eventbuilder_log_filenames = []
        self.datalogger_log_filenames = []
        self.dispatcher_log_filenames = []
        self.routingmaster_log_filenames = []

        for host in set([procinfo.host for procinfo in self.procinfos]):

            if host != "localhost":
                full_hostname = host
            else:
                full_hostname = os.environ["HOSTNAME"]
            
            res = re.search(r"^([^.]+)", full_hostname)
            assert res
            short_hostname = res.group(1)

            procinfos_for_host = [procinfo for procinfo in self.procinfos if procinfo.host == host]
            cmds = []
            proctypes = []

            for procinfo in procinfos_for_host:

                cmds.append( "ls -tr1 %s/%s-%s-%s/%s-%s-%s*.log | tail -1" % (self.log_directory,
                                                                       procinfo.label, short_hostname, procinfo.port,
                                                                       procinfo.label, short_hostname, procinfo.port) )
                proctypes.append( procinfo.name )

            cmd = "; ".join( cmds )

            if host != os.environ["HOSTNAME"] and host != "localhost":
                cmd = "ssh -f " + host + " '" + cmd + "'"

            proc = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proclines = proc.stdout.readlines()

            if len(proclines) != len(proctypes):
                self.print_log("w", "Problem associating logfiles with the artdaq processes!")
                
            for i_p in range(len(proclines)):
                if "BoardReader" in proctypes[i_p]:
                    self.boardreader_log_filenames.append("%s:%s" % (full_hostname, proclines[i_p].strip()))
                elif "EventBuilder" in proctypes[i_p]:
                    self.eventbuilder_log_filenames.append("%s:%s" % (full_hostname, proclines[i_p].strip()))
                elif "DataLogger" in proctypes[i_p]:
                    self.datalogger_log_filenames.append("%s:%s" % (full_hostname, proclines[i_p].strip()))
                elif "Dispatcher" in proctypes[i_p]:
                    self.dispatcher_log_filenames.append("%s:%s" % (full_hostname, proclines[i_p].strip()))
                elif "RoutingMaster" in proctypes[i_p]:
                    self.routingmaster_log_filenames.append("%s:%s" % (full_hostname, proclines[i_p].strip()))
                else:
                    assert False, "Unknown process type found in procinfos list"

    def softlink_logfiles(self):
        
        self.softlink_process_manager_logfiles()

        softlink_commands_to_run_on_host = {}

        for loglist in [ self.boardreader_log_filenames,
                         self.eventbuilder_log_filenames, 
                         self.datalogger_log_filenames,
                         self.dispatcher_log_filenames,
                         self.routingmaster_log_filenames ]:
            
            for fulllogname in loglist:
                host = fulllogname.split(":")[0]
                logname = "".join( fulllogname.split(":")[1:] )
                label = fulllogname.split("/")[-1].split("-")[0]

                proctype = ""

                for procinfo in self.procinfos:
                    if label == procinfo.label:
                        proctype = procinfo.name

                if "BoardReader" in proctype:
                    subdir = "boardreader"
                elif "EventBuilder" in proctype:
                    subdir = "eventbuilder"
                elif "DataLogger" in proctype:
                    subdir = "datalogger"
                elif "Dispatcher" in proctype:
                    subdir = "dispatcher"
                elif "RoutingMaster" in proctype:
                    subdir = "routingmaster"
                else:
                    assert False, "Unknown process type \"%s\" found when soflinking logfiles" % (proctype)

                if host not in softlink_commands_to_run_on_host:
                    softlink_commands_to_run_on_host[host] = []

                link_logfile_cmd = "mkdir -p %s/%s; ln -s %s %s/%s/run%d-%s.log" % \
                                   (self.log_directory, subdir, logname, self.log_directory, subdir, self.run_number, label)
                softlink_commands_to_run_on_host[host].append(link_logfile_cmd)
                
        for host in softlink_commands_to_run_on_host:
            link_logfile_cmd = "; ".join( softlink_commands_to_run_on_host[host] )

            if host != "localhost" and host != os.environ["HOSTNAME"]:
                link_logfile_cmd = "ssh %s '%s'" % (host, link_logfile_cmd)

            status = Popen(link_logfile_cmd, shell=True).wait()
            
            if status != 0:
                self.print_log("w", "WARNING: failure in performing user-friendly softlinks to logfiles on host %s" % (host))

    def get_package_version(self, package):    

        if package != "artdaq_daqinterface":
            cmd = "%s ; . %s; ups active | sed -r -n '/^%s\\s+/s/^%s\\s+(\\S+).*/\\1/p'" % \
                  (bash_unsetup_command, self.daq_setup_script, package, package)
        else:
            cmd = "ups active | sed -r -n '/^%s\\s+/s/^%s\\s+(\\S+).*/\\1/p'" % \
                  (package, package)
            
        proc =  Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdoutlines = proc.stdout.readlines()
        stderrlines = proc.stderr.readlines()

        if len(stderrlines) > 0:
            if len(stderrlines) == 1 and "type: unsetup: not found" in stderrlines[0]:
                self.print_log("w", stderrlines[0])
            else:
                raise Exception("Error in %s: the command \"%s\" yields output to stderr:\n\"%s\"" % \
                                (self.get_package_version.__name__, cmd, "".join(stderrlines)))

        if len(stdoutlines) == 0:
            raise Exception("Error in %s: the command \"%s\" yields no output to stdout" % \
                            (self.get_package_version.__name__, cmd))
            
        version = stdoutlines[-1].strip()

        if not re.search(r"v[0-9]+_[0-9]+_[0-9]+.*", version):
            raise Exception(make_paragraph("Error in %s: the version of the package \"%s\" this function has determined, \"%s\", is not the expected v<int>_<int>_<int>optionalextension format" % (self.get_package_version.__name__, package, version)))
        
        return version

    # JCF, Nov-8-2015

    # The core functionality for "do_command" is that it will launch a
    # separate thread for each transition issued to an individual
    # artdaq process; for init, start, and resume it will send the
    # command simultaneously to the aggregators, wait for the threads
    # to join, and then do the same thing for the eventbuilders and
    # then the boardreaders. For stop and pause, it will do this in
    # reverse order of upstream/downstream.

    # Note that since "initialize", "start" and "stop" all require
    # additional actions besides simply sending transitions to
    # processes and waiting for their response, "do_command" is not
    # meant to be a replacement for "do_initialize",
    # "do_start_running" and "do_stop_running" the way it IS meant to
    # be a replacement for "do_pause_running", etc., but rather, is
    # meant to be called in the body of those functions. Thus, for
    # those transitions, some functionality (e.g., announding the
    # transition is underway at the beginning of the function, and
    # calling "complete_state_change" at the end) is not applied.

    def do_command(self, command):

        if command != "Start" and command != "Init" and command != "Stop":
            self.print_log("i", "\n%s: %s transition underway" % \
                           (date_and_time(), command.upper()))

        # "process_command" is the function which will send a
        # transition to a single artdaq process, and be run on its own
        # thread so that transitions to different processes can be
        # sent simultaneously
                
        # Note that since Python is "pass-by-object-reference" (see
        # http://robertheaton.com/2014/02/09/pythons-pass-by-object-reference-as-explained-by-philip-k-dick/
        # for more), I pass it the index of the procinfo struct we
        # want, rather than the actual procinfo struct

        def process_command(self, procinfo_index, command):

            if self.exception:
                self.print_log("d", "self.exception set to true at some point, won't send %s command to %s" % \
                               (command, self.procinfos[procinfo_index].label), 2)
                return

            try:

                if command == "Init":
                    self.procinfos[procinfo_index].lastreturned = \
                        self.procinfos[procinfo_index].server.daq.init(self.procinfos[procinfo_index].fhicl_used)
                elif command == "Start":
                    self.procinfos[procinfo_index].lastreturned = \
                        self.procinfos[procinfo_index].server.daq.start(\
                        str(self.run_number))
                elif command == "Pause":
                    self.procinfos[procinfo_index].lastreturned = \
                        self.procinfos[procinfo_index].server.daq.pause()
                elif command == "Resume":
                    self.procinfos[procinfo_index].lastreturned = \
                        self.procinfos[procinfo_index].server.daq.resume()
                elif command == "Stop":
                    self.procinfos[procinfo_index].lastreturned = \
                        self.procinfos[procinfo_index].server.daq.stop()
                elif command == "Shutdown":
                    self.procinfos[procinfo_index].lastreturned = \
                        self.procinfos[procinfo_index].server.daq.shutdown()
                else:
                    assert False, "Unknown command"

                if "with ParameterSet" in self.procinfos[procinfo_index].lastreturned:
                    self.procinfos[procinfo_index].lastreturned = self.procinfos[procinfo_index].lastreturned[0:200] + \
                        " // REMAINDER TRUNCATED BY DAQINTERFACE, SEE %s FOR FULL FHiCL DOCUMENT" % (self.tmp_run_record)

            except Exception:
                self.exception = True

                pi = self.procinfos[procinfo_index]

                if "timeout: timed out" in traceback.format_exc():
                    output_message = "Timeout sending %s transition to artdaq process %s at %s:%s; try checking logfile %s for details\n" % (command, pi.label, pi.host, pi.port, self.determine_logfilename(pi))
                elif "[Errno 111] Connection refused" in traceback.format_exc():
                    output_message = "artdaq process %s at %s:%s appears to have died (or at least refused the connection) when sent the %s transition; try checking logfile %s for details" % (pi.label, pi.host, pi.port, command, self.determine_logfilename(pi))
                else:
                    self.print_log("e", traceback.format_exc())

                    output_message = "Exception caught sending %s transition to artdaq process %s at %s:%s; try checking logfile %s for details\n" % (command, pi.label, pi.host, pi.port, self.determine_logfilename(pi))

                self.print_log("e", make_paragraph(output_message))
            
            return  # From process_command

        # JCF, Nov-8-2015

        # In the code below, transition commands are sent
        # simultaneously only to classes of artdaq type. So, e.g., if
        # we're stopping, first we send stop to all the boardreaders,
        # next we send stop to all the eventbuilders, and finally we
        # send stop to all the aggregators

        proctypes_in_order = ["RoutingMaster", "Dispatcher", "DataLogger", "EventBuilder","BoardReader"]

        if command == "Stop" or command == "Pause" or command == "Shutdown":
            proctypes_in_order.reverse()

        for proctype in proctypes_in_order:

            threads = []
            priorities_used = {}

            for procinfo in self.procinfos:
                if proctype in procinfo.name:
                    priorities_used[ procinfo.priority ] = "We only care about the key in this dict"

            priority_rankings = sorted(priorities_used.iterkeys())

            for priority in priority_rankings:
                for i_procinfo, procinfo in enumerate(self.procinfos):
                    if proctype in procinfo.name and priority == procinfo.priority:
                        t = Thread(target=process_command, args=(self, i_procinfo, command))
                        threads.append(t)
                        t.start()

                for thread in threads:
                    thread.join()

        if self.exception:
            raise Exception(make_paragraph("An exception was thrown during the %s transition." % (command)))

        sleep(1)

        if self.debug_level >= 1:
            for procinfo in self.procinfos:
                self.print_log("i", "%s at %s:%s, returned string is:\n%s\n" % \
                    (procinfo.label, procinfo.host, procinfo.port, procinfo.lastreturned))


        target_states = {"Init":"Ready", "Start":"Running", "Pause":"Paused", "Resume":"Running",
                         "Stop":"Ready", "Shutdown":"Stopped"}

        try:
            self.check_proc_transition( target_states[ command ] )
        except Exception:
            raise Exception(make_paragraph("An exception was thrown during the %s transition as at least one of the artdaq processes didn't achieve its desired state." % (command)))


        if command != "Init" and command != "Start" and command != "Stop":

            verbing=""

            if command == "Pause":
                verbing = "pausing"
            elif command == "Resume":
                verbing = "resuming"
            elif command == "Shutdown":
                verbing == "shutting"
            else:
                assert False

            self.complete_state_change(self.name, verbing)
            self.print_log("i", "\n%s: %s transition complete" % (date_and_time(), command.upper()))

    def setdaqcomps(self, daq_comp_list):
        self.daq_comp_list = daq_comp_list
        self.print_log("i", "%s called with %s" % (self.setdaqcomps.__name__, 
                                                   " ".join( [ compattr for compattr in self.daq_comp_list.keys() ] )))

    def revert_failed_transition(self, failed_action):
        self.revert_state_change(self.name, self.state(self.name))
        self.print_log("e", (traceback.format_exc()))
        self.print_log("e", make_paragraph("An exception was thrown when %s; exception has been caught and system remains in the \"%s\" state" % \
                                 (failed_action, self.state(self.name))))

    # labeled_fhicl_documents is actually a list of tuples of the form
    # [ ("label", "fhicl string") ] to be saved to the process indexed
    # in self.procinfos by procinfo_index via "add_config_archive_entry"

    def archive_documents(self, labeled_fhicl_documents):

        for procinfo_index in range(len(self.procinfos)):
            if "EventBuilder" in self.procinfos[procinfo_index].name or "DataLogger" in self.procinfos[procinfo_index].name:
                if fhicl_writes_root_file(self.procinfos[procinfo_index].fhicl_used):

                    for label, contents in labeled_fhicl_documents:

                        self.print_log("d", "Saving FHiCL for %s to %s" % (label,
                                                                           self.procinfos[procinfo_index].label), 2)
                        try:
                            self.procinfos[procinfo_index].lastreturned = self.procinfos[procinfo_index].server.daq.add_config_archive_entry( label, contents )
                        except:
                            self.print_log("d", traceback.format_exc(),2)
                            self.alert_and_recover(make_paragraph("An exception was thrown when attempting to add archive entry for %s to %s" % (label, self.procinfos[procinfo_index].label)))
                            return

                        if self.procinfos[procinfo_index].lastreturned != "Success":
                            raise Exception( make_paragraph( "Attempt to add config archive entry for %s to %s was unsuccessful" % \
                                                             (label, self.procinfos[procinfo_index].label)))

    def update_archived_metadata(self):
        with open("%s/%s/metadata.txt" % ( self.record_directory, str(self.run_number) ) ) as inf:
            contents = inf.read()
            contents = re.sub("'","\"", contents)
            contents = re.sub('"', '\"', contents)

        self.archive_documents([ ("metadata", 'contents: "\n%s\n"\n' % (contents)) ])

        
    # do_boot(), do_config(), do_start_running(), etc., are the
    # functions which get called in the runner() function when a
    # transition is requested

    def do_boot(self, boot_filename = None):

        def revert_failed_boot(failed_action):
            self.reset_variables()            
            self.revert_failed_transition(failed_action)

        if not hasattr(self, "daq_comp_list") or self.daq_comp_list is None \
           or len(self.daq_comp_list) == 0:
            self.print_log("e", make_paragraph("No components appear to have been requested; you need to first call setdaqcomps (\"setdaqcomps.sh\" at the command line). System remains in \"stopped\" state."))
            self.revert_state_change(self.name, self.state(self.name))
            return

        self.print_log("i", "\n%s: BOOT transition underway" % \
            (date_and_time()))

        self.reset_variables()
        os.chdir(self.daqinterface_base_dir)

        if not boot_filename:
            boot_filename = self.run_params["boot_filename"]

        self.boot_filename = boot_filename

        try:
            self.get_boot_info( self.boot_filename )
            self.check_boot_info()
        except Exception:
            revert_failed_boot("when trying to read the DAQInterface boot file \"%s\"" % (self.boot_filename ))
            return

        if not hasattr(self, "daq_comp_list") or not self.daq_comp_list or self.daq_comp_list == {}:
            revert_failed_boot("when checking for the list of components meant to be provided by the \"setdaqcomps\" call")
            return

        for boardreader_rank, compname in enumerate(self.daq_comp_list):

            boardreader_host, boardreader_port, boardreader_subsystem = self.daq_comp_list[ compname ]

            # Make certain the formula below for calculating the port
            # # matches with the formula used to calculate the ports
            # for the other artdaq processes when the boot file is
            # read in

            if boardreader_port == "-1":
                boardreader_port = str( int(os.environ["ARTDAQ_BASE_PORT"]) + \
                                        100 + \
                                        self.partition_number*int(os.environ["ARTDAQ_PORTS_PER_PARTITION"]) + \
                                        boardreader_rank )
                self.daq_comp_list[ compname ] = boardreader_host, boardreader_port, boardreader_subsystem

            self.procinfos.append(self.Procinfo("BoardReader",
                                                boardreader_rank,
                                                boardreader_host,
                                                boardreader_port, compname, boardreader_subsystem))

            try:
                for priority, regexp in enumerate(self.boardreader_priorities):
                    if re.search(regexp, compname):
                        self.procinfos[-1].priority = priority

            except Exception:
                pass  # It's not an error if there were no boardreader priorities read in from $DAQINTERFACE_SETTINGS

        # See the Procinfo.__lt__ function for details on sorting

        self.procinfos.sort()

        # JCF, Oct-18-2017

        # After a discussion with Ron about how trace commands need to
        # be run on the host that the artdaq process is running on, we
        # agreed it would be a good idea to do a pass in which the
        # setup script was sourced on all hosts which artdaq processes
        # ran on in case the setup script contained trace commands...

        # JCF, Jan-17-2018

        # It turns out that sourcing the setup script on hosts for
        # runs which use lots of nodes takes an onerously long
        # time. What we'll do now is source the script on just ONE
        # node, to make sure it's not broken. Note that this means you
        # may need to perform a second run after adding TRACE
        # functionality to your setup script; while a cost, the
        # benefit here seems to outweight the cost.

        if self.manage_processes:

            hosts = [procinfo.host for procinfo in self.procinfos]
            random_host = random.choice( hosts )

            starttime = time()
            self.print_log("i", "\nOn randomly selected node (%s), checking that the setup file %s doesn't return a nonzero value when sourced..." % \
                           (random_host, self.daq_setup_script), 1, False)

            with deepsuppression(self.debug_level < 3):
                cmd = "%s ; . %s" % (bash_unsetup_command, self.daq_setup_script)

                if random_host != "localhost" and random_host != os.environ["HOSTNAME"]:
                    cmd = "ssh %s '%s'" % (random_host, cmd)

                out = Popen(cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

                out_comm = out.communicate()

                out_stdout = out_comm[0]
                out_stderr = out_comm[1]
                status = out.returncode

            if status != 0:
                self.print_log("e", "\nNonzero value (%d) returned in attempt to source script %s on host \"%s\"." % \
                               (status, self.daq_setup_script, random_host))
                self.print_log("e", "STDOUT: \n%s" % (out_stdout))
                self.print_log("e", "STDERR: \n%s" % (out_stderr))
                raise Exception("Nonzero value (%d) returned in attempt to source script %s on host %s." % \
                                (status, self.daq_setup_script, random_host))
            
            endtime = time()
            self.print_log("i", "done (%.1f seconds)." % (endtime - starttime))

        if self.manage_processes:
            
            for ss in self.subsystems:
                self.print_log("d", "Subsystem %s, source subsystem %s, destination subsystem %s" % 
                               (ss, self.subsystems[ss].source, self.subsystems[ss].destination), 2)

            for procinfo in self.procinfos:
                self.print_log("d", "%s at %s:%s, part of subsystem %s, has rank %s" % (procinfo.label, procinfo.host, procinfo.port, procinfo.subsystem, procinfo.rank), 2)
 
            # Ensure the needed log directories are in place

            logdir_commands_to_run_on_host = []

            for logdir in ["pmt", "boardreader", "eventbuilder",
                           "dispatcher", "datalogger", "routingmaster"]:
                logdir_commands_to_run_on_host.append("mkdir -p -m 0777 " + "%s/%s" % (self.log_directory, logdir) )

            for host in set([procinfo.host for procinfo in self.procinfos]):
                logdircmd = construct_checked_command( logdir_commands_to_run_on_host )

                if host != os.environ["HOSTNAME"] and host != "localhost":
                    logdircmd = "ssh -f " + host + " '" + logdircmd + "'"

                with deepsuppression(self.debug_level < 4):
                    proc = Popen(logdircmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    status = proc.wait()

                if status != 0:   
                    self.print_log("e", "\nNonzero return value (%d) resulted when trying to run the following on host %s:\n%s\n" % \
                                   (status, host, "\n".join(logdir_commands_to_run_on_host)))
                    self.print_log("e", "STDOUT output: \n%s" % ("\n".join(proc.stdout.readlines())))
                    self.print_log("e", "STDERR output: \n%s" % ("\n".join(proc.stderr.readlines())))
                    raise Exception("Problem running mkdir -p for the needed logfile directories on %s" % ( host ) )

            # Now, with the info on hand about the processes contained in
            # procinfos, actually launch them

            self.print_log("i", "Launching the artdaq processes")
            self.called_launch_procs = True

            try:
                launch_procs_actions = self.launch_procs()

                assert type( launch_procs_actions ) is dict, \
                    make_paragraph("The launch_procs function needs to return a dictionary whose keys are the names of the hosts on which it ran commands, and whose values are those commands")
                
            except Exception:
                self.print_log("e", traceback.format_exc())

                self.alert_and_recover("An exception was thrown in launch_procs(), see traceback above for more info")
                return

            num_launch_procs_checks = 0
            max_num_launch_procs_checks = 5

            while True:

                num_launch_procs_checks += 1

                self.print_log("i", "Checking that processes are up (check %d of a max of %d)..." % \
                               (num_launch_procs_checks, max_num_launch_procs_checks), 1, False)

                # "False" here means "don't consider it an error if all
                # processes aren't found"

                found_processes = self.check_proc_heartbeats(False)
                self.print_log("i", "found %d of %d processes." % (len(found_processes), len(self.procinfos)))

                assert type(found_processes) is list, \
                    make_paragraph("check_proc_heartbeats needs to return a list of procinfos corresponding to the processes it found alive")
                if len(found_processes) == len(self.procinfos):

                    self.print_log("i", "All processes appear to be up")

                    break
                else:
                    sleep(2)
                    if num_launch_procs_checks >= max_num_launch_procs_checks:
                        missing_processes = [procinfo for procinfo in self.procinfos if procinfo not in found_processes]

                        print
                        self.print_log("e", "The following desired artdaq processes failed to launch:\n%s" % \
                                       (", ".join(["%s at %s:%s" % (procinfo.label, procinfo.host, procinfo.port) for procinfo in missing_processes])))
                        self.print_log("e", make_paragraph("In order to investigate what happened, you can try re-running with \"debug level\" in your boot file set to 4. If that doesn't help, you can directly recreate what DAQInterface did by doing the following:"))
                        
                        for host in set([procinfo.host for procinfo in self.procinfos if procinfo in missing_processes]):

                            self.print_log("i", "\nPerform a clean login to %s, source the DAQInterface environment, and execute the following:\n%s" % \
                                           (host, "\n".join(launch_procs_actions[ host ])))
                        
                        self.process_launch_diagnostics(missing_processes)

                        self.alert_and_recover("Problem launching the artdaq processes; scroll above the output from the \"RECOVER\" transition for more info")
                        return

            for procinfo in self.procinfos:

                if "BoardReader" in procinfo.name:
                    timeout = self.boardreader_timeout
                elif "EventBuilder" in procinfo.name:
                    timeout = self.eventbuilder_timeout
                elif "RoutingMaster" in procinfo.name:
                    timeout = self.routingmaster_timeout
                elif "DataLogger" in procinfo.name:
                    timeout = self.datalogger_timeout
                elif "Dispatcher" in procinfo.name:
                    timeout = self.dispatcher_timeout

                try:
                    procinfo.server = TimeoutServerProxy(
                        procinfo.socketstring, timeout)
                except Exception:
                    self.print_log("e", traceback.format_exc())

                    self.alert_and_recover("Problem creating server with socket \"%s\"" % \
                                               procinfo.socketstring)
                    return

        if self.use_messageviewer:

            # Use messageviewer if it's available, i.e., if there's
            # one already up or if it's set up via the user-supplied
            # setup script

            try:

                if self.have_artdaq_mfextensions() and is_msgviewer_running():
                    self.print_log("i", make_paragraph("An instance of messageviewer already appears to be running; " + \
                                             "messages will be sent to the existing messageviewer"))
                elif self.have_artdaq_mfextensions():
                    version, qualifiers = self.artdaq_mfextensions_info()

                    self.print_log("i", make_paragraph("artdaq_mfextensions %s, %s, appears to be available; "
                                              "if windowing is supported on your host you should see the "
                                              "messageviewer window pop up momentarily" % \
                                                  (version, qualifiers)))

                    cmds = []
                    port_to_replace = 30000
                    msgviewer_fhicl = "/tmp/msgviewer_partition%d_%s.fcl" % (self.partition_number, os.environ["USER"])
                    cmds.append(bash_unsetup_command)
                    cmds.append(". %s" % (self.daq_setup_script))
                    cmds.append("which msgviewer")
                    cmds.append("cp $ARTDAQ_MFEXTENSIONS_DIR/fcl/msgviewer.fcl %s" % (msgviewer_fhicl))
                    cmds.append("res=$( grep -l \"port: %d\" %s )" % (port_to_replace, msgviewer_fhicl))
                    cmds.append("if [[ -n $res ]]; then true ; else false ; fi")
                    cmds.append("sed -r -i 's/port: [^\s]+/port: %d/' %s" % (10005 + self.partition_number*1000, msgviewer_fhicl))
                    cmds.append("msgviewer -c %s 2>&1 > /dev/null &" % (msgviewer_fhicl))

                    msgviewercmd = construct_checked_command( cmds )

                    with deepsuppression(self.debug_level < 3):
                        status = Popen(msgviewercmd, shell=True).wait()

                    if status != 0:
                        self.alert_and_recover("Status error raised in msgviewer call within Popen; tried the following commands: \n\n\"%s\"" %
                                            " ;\n".join(cmds) )
                        return
                else:
                    self.print_log("i", make_paragraph("artdaq_mfextensions does not appear to be available; "
                                         "unable to launch the messageviewer window. This will not affect"
                                         " actual datataking, it just means you'll need to look at the"
                                         " logfiles to see artdaq output."))

            except Exception:
                self.print_log("e", traceback.format_exc())
                self.alert_and_recover("Problem during messageviewer launch stage")
                return

        if self.manage_processes:
            # JCF, 3/5/15

            # Get our hands on the name of logfile so we can save its
            # name for posterity. This is taken to be the most recent
            # logfile found in the log directory. There's a tiny chance
            # someone else's logfile could sneak in during the few seconds
            # taken during startup, but it's unlikely...
            
            starttime=time()
            self.print_log("i", "\nDetermining logfiles associated with the artdaq processes...", 1, False)

            try:

                self.process_manager_log_filenames = self.get_process_manager_log_filenames()
                self.get_artdaq_log_filenames()

            except Exception:
                self.print_log("e", traceback.format_exc())
                self.alert_and_recover("Problem obtaining logfile name(s)")
                return
            endtime = time()
            self.print_log("i", "done (%.1f seconds)." % (endtime - starttime))

        self.complete_state_change(self.name, "booting")

        self.print_log( "i", "\n%s: BOOT transition complete" % \
                        (date_and_time()))


    def do_config(self, subconfigs_for_run = [] ):

        self.print_log("i", "\n%s: CONFIG transition underway" % \
            (date_and_time()))

        os.chdir(self.daqinterface_base_dir)

        if not subconfigs_for_run:
            self.subconfigs_for_run = self.run_params["config"]
        else:
            self.subconfigs_for_run = subconfigs_for_run

        self.subconfigs_for_run.sort() 

        self.print_log("d", "Config name: %s" % ( " ".join(self.subconfigs_for_run) ), 1)
        self.print_log("d", "Selected DAQ comps: %s" % self.daq_comp_list, 2)

        starttime=time()
        self.print_log("i", "\nObtaining FHiCL documents...", 1, False)

        try:
            tmpdir_for_fhicl, self.fhicl_file_path = self.get_config_info()
            assert "/tmp" == tmpdir_for_fhicl[:4]
            self.print_log("d", "Using temporary fhicl directory %s" % tmpdir_for_fhicl,2)
        except:
            self.revert_failed_transition("calling get_config_info()")
            return

        for ffp_path in self.fhicl_file_path:
            self.print_log("d", "\tIncluding FHICL FILE PATH %s" % ffp_path,2)

        rootfile_cntr = 0 

        filename_dictionary = {}  # If we find a repeated *.fcl file, that's an error
        
        for dummy, dummy, filenames in os.walk( tmpdir_for_fhicl ):        
            for filename in filenames:
                if filename.endswith(".fcl"):
                    if filename not in filename_dictionary:
                        filename_dictionary[ filename ] = True

                        # See Issue #20803. Idea is that, e.g., component01.fcl and component01_hw_cfg.fcl 
                        # refer to the same thing

                        if filename.endswith("_hw_cfg.fcl"):
                            filename_dictionary[ filename.replace("_hw_cfg.fcl", ".fcl") ] = True 
                        else:
                            filename_dictionary[ filename.replace(".fcl", "_hw_cfg.fcl") ] = True 
                    else:
                        raise Exception(make_paragraph("Error: filename \"%s\" found more than once given the set of requested subconfigurations \"%s\" (see %s)" % \
                                                       (filename, " ".join(self.subconfigs_for_run), tmpdir_for_fhicl)))

        for i_proc in range(len(self.procinfos)):

            matching_filenames = [ "%s.fcl" % self.procinfos[i_proc].label ]
            if "BoardReader" in self.procinfos[i_proc].name:  # For backwards compatibility (see Issue #20803)
                matching_filenames.append( "%s_hw_cfg.fcl" % self.procinfos[i_proc].label )

            found_fhicl = False
            for dirname, dummy, filenames in os.walk( tmpdir_for_fhicl ):
                for filename in filenames:
                    if filename in matching_filenames:
                        fcl = "%s/%s" % (dirname, filename)
                        found_fhicl = True
                        self.print_log("d", "Found FHiCL document for %s called %s" % (self.procinfos[i_proc].label, fcl), 2)

            if not found_fhicl:
                self.print_log("e", make_paragraph("Unable to find a FHiCL document for %s in configuration \"%s\"; either remove the request for %s in the setdaqcomps.sh command (boardreader) or boot file (other artdaq process types) and redo the transitions or choose a new configuration" % \
                                                      (self.procinfos[i_proc].label, " ".join(self.subconfigs_for_run),
                                                       self.procinfos[i_proc].label)))
                self.revert_failed_transition("looking for all needed FHiCL documents")
                return

            try:
                self.procinfos[i_proc].ffp = self.fhicl_file_path
                self.procinfos[i_proc].update_fhicl(fcl)
            except Exception:
                self.print_log("e", traceback.format_exc())
                self.alert_and_recover("An exception was thrown when creating the process FHiCL documents; see traceback above for more info")
                return

            if not self.disable_unique_rootfile_labels and \
               ("EventBuilder" in self.procinfos[i_proc].name or "DataLogger" in self.procinfos[i_proc].name):
                fhicl_before_sub = self.procinfos[i_proc].fhicl_used

                if self.procinfos[i_proc].name == "DataLogger":
                    rootfile_cntr_prefix = "dl"
                elif self.procinfos[i_proc].name == "EventBuilder":
                    rootfile_cntr_prefix = "eb"

                self.procinfos[i_proc].fhicl_used = re.sub(r'(\n\s*[^#\s].*)\.root',
                                                       r"\1" + "_" + str(rootfile_cntr_prefix) + 
                                                       str(rootfile_cntr+1) + ".root",
                                                       self.procinfos[i_proc].fhicl_used)

                if self.procinfos[i_proc].fhicl_used != fhicl_before_sub:
                    rootfile_cntr += 1

        endtime=time()
        self.print_log("i", "done (%.1f seconds)." % (endtime - starttime))

        for procinfo in self.procinfos:
            assert not procinfo.fhicl is None and not procinfo.fhicl_used is None

        assert "/tmp" == tmpdir_for_fhicl[:4] and len(tmpdir_for_fhicl) > 4
        shutil.rmtree( tmpdir_for_fhicl )

        starttime=time()
        self.print_log("i", "Bookkeeping the FHiCL documents...", 1, False)

        try:
            self.bookkeeping_for_fhicl_documents()
        except Exception:
            self.print_log("e", traceback.format_exc())
            self.alert_and_recover("An exception was thrown when performing bookkeeping on the process FHiCL documents; see traceback above for more info")
            return
        endtime=time()
        self.print_log("i", "done (%.1f seconds)." % (endtime-starttime))

        starttime=time()
        self.print_log("i", "Reformatting the FHiCL documents...", 1, False)

        if not os.path.exists(os.environ["DAQINTERFACE_SETUP_FHICLCPP"]):
            self.print_log("w", make_paragraph("File \"%s\", needed for formatting FHiCL configurations, does not appear to exist; will attempt to auto-generate one..." % (os.environ["DAQINTERFACE_SETUP_FHICLCPP"])))
            with open( os.environ["DAQINTERFACE_SETUP_FHICLCPP"], "w") as outf:
                outf.write("source %s/setup\n" % (self.productsdir))
                outf.write( bash_unsetup_command + "\n" )
                lines = Popen("export PRODUCTS= ; source %s/setup; ups list -aK+ fhiclcpp | sort -n" % (self.productsdir), 
                                               shell=True, stdout=subprocess.PIPE).stdout.readlines()
                if len(lines) > 0:
                    fhiclcpp_to_setup_line = lines[-1]
                else:
                    os.unlink( os.environ["DAQINTERFACE_SETUP_FHICLCPP"] )
                    raise Exception(make_paragraph("Unable to find fhiclcpp ups product in products directory \"%s\" provided in the DAQInterface settings file, \"%s\"" % (self.productsdir, os.environ["DAQINTERFACE_SETTINGS"])))

                outf.write("setup %s %s -q %s\n" % (fhiclcpp_to_setup_line.split()[0],
                                                  fhiclcpp_to_setup_line.split()[1],
                                                  fhiclcpp_to_setup_line.split()[3]))

            if os.path.exists( os.environ["DAQINTERFACE_SETUP_FHICLCPP"] ):
                self.print_log("w", "\"%s\" has been auto-generated; you may want to check to see that it correctly sets up the fhiclcpp package..." % (os.environ["DAQINTERFACE_SETUP_FHICLCPP"]))
            else:
                raise Exception(make_paragraph("Error: was unable to find or create a file \"%s\"" % (os.environ["DAQINTERFACE_SETUP_FHICLCPP"])))
        with deepsuppression(self.debug_level < 2):
            reformatted_fhicl_documents = reformat_fhicl_documents(os.environ["DAQINTERFACE_SETUP_FHICLCPP"], self.procinfos)

        for i_proc, reformatted_fhicl_document in enumerate(reformatted_fhicl_documents):
            self.procinfos[i_proc].fhicl_used = reformatted_fhicl_document
        
        endtime=time()
        self.print_log("i", "done (%.1f seconds)." % (endtime - starttime))

        self.tmp_run_record = "/tmp/run_record_attempted_%s/%s" % \
            (os.environ["USER"],
            Popen("date +%a_%b_%d_%H:%M:%S.%N", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip())
        
        if os.path.exists(self.tmp_run_record):
            shutil.rmtree(self.tmp_run_record)

        starttime = time()
        self.print_log("i", "Saving the run record...", 1, False)

        try:
            self.save_run_record()            
        except Exception:
            self.print_log("w", traceback.format_exc())
            self.print_log("w", make_paragraph(
                    "WARNING: an exception was thrown when attempting to save the run record. While datataking may be able to proceed, this may also indicate a serious problem"))

        endtime = time()
        self.print_log("i", "done (%.1f seconds)." % (endtime - starttime))

        if self.manage_processes:

            try:
                self.do_command("Init")
            except Exception:
                self.print_log("d", traceback.format_exc(),2)
                self.alert_and_recover("An exception was thrown when attempting to send the \"init\" transition to the artdaq processes; see messages above for more info")
                return

            try:
                self.launch_art_procs(self.boot_filename)
            except Exception:
                self.print_log("w", traceback.format_exc())
                self.print_log("w", make_paragraph("WARNING: an exception was caught when trying to launch the online monitoring processes; online monitoring won't work though this will not affect actual datataking"))

            starttime=time()
            self.print_log("i", "Ensuring FHiCL documents will be archived in the output *.root files...", 1, False)

            labeled_fhicl_documents = []

            for procinfo_with_fhicl_to_save in self.procinfos:
                labeled_fhicl_documents.append( (procinfo_with_fhicl_to_save.label, \
                                                 re.sub("'","\"", procinfo_with_fhicl_to_save.fhicl_used)) )

            for filestub in ["metadata", "boot" ]:
                with open("%s/%s.txt" % ( self.tmp_run_record, filestub ) ) as inf:
                    contents = inf.read()
                    contents = re.sub("'","\"", contents)
                    contents = re.sub('"', '\"', contents)
                    labeled_fhicl_documents.append( (filestub,
                                                     'contents: "\n%s\n"\n' % (contents)) )

            self.archive_documents(labeled_fhicl_documents)

            endtime = time()
            self.print_log("i", "done (%.1f seconds)." % (endtime - starttime))

        self.complete_state_change(self.name, "configuring")

        if self.manage_processes:
            self.print_log("i", "\nProcess manager logfiles (if applicable):\n%s" % (", ".join(self.process_manager_log_filenames)))

        self.print_log("i", "\n%s: CONFIG transition complete" % (date_and_time()))

    def do_start_running(self, run_number = None):

        if not run_number:
            self.run_number = self.run_params["run_number"]
        else:
            self.run_number = run_number

        self.print_log("i", "\n%s: START transition underway for run %d" % \
                       (date_and_time(), self.run_number))
        
        if os.path.exists( self.tmp_run_record ):
            run_record_directory = "%s/%s" % \
                (self.record_directory, str(self.run_number))

            cmd = "cp -r %s %s" % (self.tmp_run_record, run_record_directory)
            status = Popen(cmd, shell = True).wait()

            if status != 0:
                self.alert_and_recover("Error in DAQInterface: a nonzero value was returned executing \"%s\"" %
                                       cmd)
                return
        else:
            self.alert_and_recover("Error in DAQInterface: unable to find temporary run records directory %s" % 
                                   self.tmp_run_record)
            return

        starttime = time()
        self.print_log("i,", "Attempting to save config info to the database, if in use...", 1, False);

        try:
            self.put_config_info()
        except Exception:
            self.print_log("e", traceback.format_exc())
            self.alert_and_recover("An exception was thrown when trying to save configuration info; see traceback above for more info")
            return

        endtime = time()
        self.print_log("i", "done (%.1f seconds)." % (endtime - starttime))


        if self.manage_processes:

            try:
                self.do_command("Start")
            except Exception:
                self.print_log("d", traceback.format_exc(),2)
                self.alert_and_recover("An exception was thrown when attempting to send the \"start\" transition to the artdaq processes; see messages above for more info")
                return
            
        self.start_datataking()

        self.save_metadata_value("Start time", \
                                     Popen("date --utc", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip() )

        if self.manage_processes:
            starttime=time()
            self.print_log("i,", "Attempting to provide run-numbered softlinks to the logfiles...", 1, False);
            self.softlink_logfiles()
            endtime=time()
            self.print_log("i", "done (%.1f seconds)." % (endtime - starttime))

        self.print_log("i", "\nRun info can be found locally at %s\n" % \
                (run_record_directory))

        self.complete_state_change(self.name, "starting")
        self.print_log("i", "\n%s: START transition complete for run %d" % \
            (date_and_time(), self.run_number))

    def do_stop_running(self):

        self.print_log("i", "\n%s: STOP transition underway for run %d" % \
            (date_and_time(), self.run_number))

        self.save_metadata_value("Stop time", \
                                     Popen("date --utc", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip() )

        self.stop_datataking()

        if self.manage_processes:

            try:
                self.do_command("Stop")
            except Exception:
                self.print_log("d", traceback.format_exc(),2)
                self.alert_and_recover("An exception was thrown when attempting to send the \"stop\" transition to the artdaq processes; see messages above for more info")
                return

        self.complete_state_change(self.name, "stopping")
        self.print_log("i", "\n%s: STOP transition complete for run %d" % \
            (date_and_time(), self.run_number))

    def do_terminate(self):

        self.print_log("i", "\n%s: TERMINATE transition underway" % \
            (date_and_time()))

        print

        if hasattr(self, "tmp_run_record") and os.path.exists(self.tmp_run_record):
            shutil.rmtree(self.tmp_run_record)

        if self.manage_processes:

            self.process_manager_cleanup()

            for procinfo in self.procinfos:

                try:
                    procinfo.lastreturned = procinfo.server.daq.shutdown()
                except Exception:
                    self.print_log("e", "DAQInterface caught an exception in "
                                   "do_terminate()")
                    self.print_log("e", traceback.format_exc())

                    self.print_log("e", "%s at %s:%s, returned string is:\n%s\n" % \
                                       (procinfo.label, procinfo.host, procinfo.port, procinfo.lastreturned))

                    self.alert_and_recover("An exception was thrown "
                                           "during the terminate transition")
                    return
                else:
                    self.print_log("i", "%s at %s:%s, returned string is:\n%s\n" % \
                                   (procinfo.label, procinfo.host, procinfo.port, procinfo.lastreturned), 1)
            try:
                self.kill_procs()
            except Exception:
                self.print_log("e", "DAQInterface caught an exception in "
                               "do_terminate()")
                self.print_log("e", traceback.format_exc())
                self.alert_and_recover("An exception was thrown "
                                       "within kill_procs()")
                return

        self.complete_state_change(self.name, "terminating")

        self.print_log("i", "\n%s: TERMINATE transition complete" % (date_and_time()))

        if self.manage_processes:
            self.print_log("i", "Process manager logfiles (if applicable): %s" % (",".join(self.process_manager_log_filenames)))

    def do_recover(self):
        print
        self.print_log("w", "\n%s: RECOVER transition underway" % \
            (date_and_time()))

        self.in_recovery = True

        if not self.called_launch_procs:
            self.print_log("i", "DAQInterface does not appear to have gotten to the point of launching the artdaq processes")

        if self.disable_recovery or not self.called_launch_procs:
            self.print_log("i", "Skipping cleanup of artdaq processes, this recover step is effectively a no-op")

            self.in_recovery = False
            self.complete_state_change(self.name, "recovering")
            self.print_log("i", "\n%s: RECOVER transition complete" % (date_and_time()))
            return

        self.called_launch_procs = False

        def attempted_stop(self, procinfo):

            pid = self.get_pid_for_process(procinfo)

            if pid is None:
                if self.debug_level >= 2 or not self.heartbeat_failure:
                    self.print_log("d", 
                        "Didn't find PID for %s at %s:%s" % (procinfo.label, procinfo.host, procinfo.port), 2)
                return

            def send_recover_command(command):
                
                try:
                    if command == "stop":
                        lastreturned=procinfo.server.daq.stop()
                    elif command == "shutdown":
                        lastreturned=procinfo.server.daq.shutdown()
                    else:
                        assert False

                    self.print_log("d", "Called %s on %s at %s:%s without an exception; returned string was \"%s\"" % \
                                       (command, procinfo.label, procinfo.host, procinfo.port, lastreturned), 2)
                except Exception:
                    raise

                if lastreturned == "Success":
                    self.print_log("d", "Successful %s sent to %s at %s:%s" % \
                                       (command, procinfo.label, procinfo.host, procinfo.port), 2)
                else:
                    raise Exception( make_paragraph( \
                                                     "Attempted %s sent to artdaq process %s " % (command, procinfo.label) + \
                                "at %s:%s during recovery procedure" % (procinfo.host, procinfo.port) + \
                                " returned \"%s\"" % \
                                (lastreturned)))

            try:
                procstatus = procinfo.server.daq.status()
            except Exception:
                msg = "Unable to determine state of artdaq process %s at %s:%s; will not be able to complete its stop-and-shutdown" % \
                                   (procinfo.label, procinfo.host, procinfo.port)
                if self.state(self.name) != "stopped" and self.state(self.name) != "booting" and self.state(self.name) != "terminating":
                    self.print_log("e", make_paragraph(msg))
                else:
                    self.print_log("d", make_paragraph(msg), 2)
    
                return

            if procstatus == "Running":

                try:
                    send_recover_command("stop")
                except Exception:
                    if "ProtocolError" not in traceback.format_exc():
                        self.print_log("e", traceback.format_exc())
                    self.print_log("e",  make_paragraph( 
                            "Exception caught during stop transition sent to artdaq process %s " % (procinfo.label) +
                            "at %s:%s during recovery procedure;" % (procinfo.host, procinfo.port) +
                            " it's possible the process no longer existed\n"))
                        
                    return
                    
                try:
                    procstatus = procinfo.server.daq.status()
                except Exception:
                    self.print_log("e", "Unable to determine state of artdaq process %s at %s:%s; will not be able to complete its stop-and-shutdown" % \
                                       (procinfo.label, procinfo.host, procinfo.port))
                    return

            if procstatus == "Ready":

                try:
                    send_recover_command("shutdown")
                except Exception:
                    if "ProtocolError" not in traceback.format_exc():
                        self.print_log("e", traceback.format_exc())
                    self.print_log("e",  make_paragraph( 
                            "Exception caught during shutdown transition sent to artdaq process %s " % (procinfo.label) +
                            "at %s:%s during recovery procedure;" % (procinfo.host, procinfo.port) +
                            " it's possible the process no longer existed\n"))
                    return

            return
        

        if self.manage_processes:

            # JCF, Feb-1-2017

            # If an artdaq process has died, the others might follow
            # soon after - if this is the case, then wait a few
            # seconds to give them a chance to die before trying to
            # send them transitions (i.e., so they don't die AFTER a
            # transition is sent, causing more errors)

            if self.heartbeat_failure:
                sleep_on_heartbeat_failure = 0

                self.print_log("d", 
                               make_paragraph(
                                   "A process previously was found to be missing; " +
                                   "therefore will wait %d seconds before attempting to send the normal transitions as part of recovery" % \
                                   (sleep_on_heartbeat_failure)), 2)
                sleep(sleep_on_heartbeat_failure)  


            print
            for name in ["BoardReader", "EventBuilder", "DataLogger", "Dispatcher", "RoutingMaster"]:

                self.print_log("i", "%s: Attempting to cleanly wind down the %ss if they still exist" % (date_and_time(), name))

                threads = []
                priorities_used = {}

                for procinfo in self.procinfos:
                    if name in procinfo.name:
                        priorities_used[ procinfo.priority ] = "We only care about the key in the dict"

                for priority in sorted(priorities_used.iterkeys(), reverse = True):
                    for procinfo in self.procinfos:
                        if name in procinfo.name and priority == procinfo.priority:
                            t = Thread(target=attempted_stop, args=(self, procinfo))
                            threads.append(t)
                            t.start()

                    for thread in threads:
                        thread.join()

        if self.manage_processes:
            print
            self.print_log("i", "%s: Attempting to kill off the artdaq processes from this run if they still exist" % (date_and_time()))
            try:
                self.kill_procs()
            except Exception:
                self.print_log("e", traceback.format_exc())
                self.print_log("e", make_paragraph("An exception was thrown "
                                       "within kill_procs(); artdaq processes may not all have been killed"))

        self.in_recovery = False

        self.complete_state_change(self.name, "recovering")

        self.print_log("i", "\n%s: RECOVER transition complete" % (date_and_time()))

    # Override of the parent class Component's runner function. As of
    # 5/30/14, called every 1s by control.py

    def runner(self):
        """
        Component "ops" loop.  Called at threading hearbeat frequency,
        currently 1/sec.
        """

        try:

            if self.in_recovery:
                pass

            elif self.__do_boot:
                self.__do_boot = False
                self.do_boot()

            elif self.__do_shutdown:
                self.__do_shutdown = False
                self.do_command("Shutdown")


            elif self.__do_config:
                self.__do_config = False
                self.do_config()


            elif self.__do_recover:
                self.__do_recover = False
                self.do_recover()


            elif self.__do_start_running:
                self.__do_start_running = False
                self.do_start_running()


            elif self.__do_stop_running:
                self.__do_stop_running = False
                self.do_stop_running()


            elif self.__do_terminate:
                self.__do_terminate = False
                self.do_terminate()


            elif self.__do_pause_running:
                self.__do_pause_running = False
                self.do_command("Pause")


            elif self.__do_resume_running:
                self.__do_resume_running = False
                self.do_command("Resume")

            elif self.__do_enable:
                self.__do_enable = False
                self.do_enable()

            elif self.__do_disable:
                self.__do_disable = False
                self.do_disable()

            elif self.manage_processes and self.state(self.name) != "stopped" and self.state(self.name) != "booting" and self.state(self.name) != "terminating":
                self.check_proc_heartbeats()
                self.check_proc_exceptions()

        except Exception:
            self.in_recovery = True
            self.alert_and_recover(traceback.format_exc())
            self.in_recovery = False


def get_args():  # no-coverage
    parser = argparse.ArgumentParser(
        description="DAQInterface")
    parser.add_argument("-n", "--name", type=str, dest='name',
                        default="daqint", help="Component name")
    parser.add_argument("-p", "--partition-number", type=int, dest='partition_number',
                        default=888, help="Partition number")
    parser.add_argument("-r", "--rpc-port", type=int, dest='rpc_port',
                        default=5570, help="RPC port")
    parser.add_argument("-H", "--rpc-host", type=str, dest='rpc_host',
                        default='localhost', help="This hostname/IP addr")
    parser.add_argument("-c", "--control-host", type=str, dest='control_host',
                        default='localhost', help="Control host")

    return parser.parse_args()


def main():  # no-coverage

    one_daqinterface_per_host = False

    greptoken = "python.*daqinterface.py"
    pids = get_pids(greptoken)

    if len(pids) > 1 and one_daqinterface_per_host:
        print make_paragraph("Won't launch DAQInterface; it appears an instance is already running on this host according to this command:" )
        print "\nps aux | grep \"%s\" | grep -v grep\n" % (greptoken)
        return

    if "DAQINTERFACE_STANDARD_SOURCEFILE_SOURCED" not in os.environ.keys():
        print make_paragraph("Won't launch DAQInterface; you first need to run \"source $ARTDAQ_DAQINTERFACE_DIR/source_me\"")
        print
        return

    if "DAQINTERFACE_SETTINGS" not in os.environ.keys():
        print make_paragraph("Need to have the DAQINTERFACE_SETTINGS environment variable set to refer to the DAQInterface settings file")
        print
        return

    if not os.path.exists( os.environ["DAQINTERFACE_SETTINGS"] ):
        print make_paragraph("The file referred to by the DAQINTERFACE_SETTINGS environment variable, \"%s\", does not appear to exist" % (os.environ["DAQINTERFACE_SETTINGS"]))
        print
        return

    if "DAQINTERFACE_KNOWN_BOARDREADERS_LIST" not in os.environ.keys():
        print make_paragraph("Need to have the DAQINTERFACE_KNOWN_BOARDREADERS_LIST environment variable set to refer to the list of boardreader types DAQInterface can use")
        print
        return

    if not os.path.exists( os.environ["DAQINTERFACE_KNOWN_BOARDREADERS_LIST"] ):
        print make_paragraph("The file referred to by the DAQINTERFACE_KNOWN_BOARDREADERS_LIST environment variable, \"%s\", does not appear to exist" % (os.environ["DAQINTERFACE_KNOWN_BOARDREADERS_LIST"]))
        print
        return

    args = get_args()

    # Make sure the requested partition number is in a desired range,
    # and that it isn't already being used

    max_partitions = 10
    assert "partition_number" in vars(args)
    partition_number = vars(args)["partition_number"]
    if partition_number < 0 or partition_number > max_partitions - 1:
        print
        print make_paragraph(
            "Error: requested partition has the value %d while it needs to be between 0 and %d, inclusive; please set the DAQINTERFACE_PARTITION_NUMBER environment variable accordingly and try again" % \
            (partition_number, max_partitions-1))
        return

    greptoken = "python.*daqinterface.py.*--partition-number\s\+%d\s\+" % (partition_number)
    pids = get_pids(greptoken)
    if len(pids) > 1:  
        print make_paragraph("There already appears to be a DAQInterface instance running on the requested partition number (%s); please either kill the instance (if it's yours) or use a different partition. Run \"listdaqinterfaces.sh\" for more info." % (partition_number))
        return


    with DAQInterface(logpath=os.path.join(os.environ["HOME"], ".lbnedaqint.log"),
                      **vars(args)):
        try:
            while True:
                sleep(100)
        except: KeyboardInterrupt

if __name__ == "__main__":
    main()
