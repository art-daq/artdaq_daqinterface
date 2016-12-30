
import subprocess
from subprocess import Popen

import re
import os
import string

import sys
sys.path.append( os.getcwd() )

from rc.control.utilities import expand_environment_variable_in_string

def config_basedir():
    return os.environ["HOME"] + "/daqarea/work-db-dir"

def setup_database_commands():

    if not os.path.exists( config_basedir() ):
        raise Exception("Error in %s: unable to locate expected database configuration directory \"%s\"" % \
                            (setup_database_commands.__name__, config_basedir()))

    sourcemefile = os.environ["HOME"] + "/.database.bash.rc"

    if not os.path.exists( sourcemefile ):
        raise Exception("Error in %s: unable to locate expected database environment file to source, \"%s\"" % \
                            (setup_database_commands.__name__, sourcemefile))

    cmds = []
    cmds.append( ". " + sourcemefile )
    cmds.append( "cd %s" % (config_basedir()) )
    return cmds

def execute_commands_and_throw_if_problem(cmds):

    proc = Popen("; ".join(cmds), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output_lines = proc.stdout.readlines()
    
    if len(output_lines) == 0:
        raise Exception("Error: No lines of output from execution of the following: \n\"%s\"" % \
                            ("; ".join(cmds) ))

    elif "Return status: succeed" not in output_lines[-1]:
        raise Exception("Error: execution of the following \"%s\" resulted in " \
                            "the following output: \"%s\"" % ("; ".join(cmds), "".join( output_lines )))


def get_config_info_base(self):

    cmds = setup_database_commands()

    cmds.append( "conftool.sh -o export_global_config -g " + self.config_for_run)

    execute_commands_and_throw_if_problem( cmds )
    
    configdir = "%s/newconfig/" % (config_basedir())
    return configdir, [ configdir ]


def put_config_info_base(self):

    scriptdir = os.environ["PWD"] + "/utils"

    if not os.path.exists( scriptdir ):
        self.alert_and_recover("Error: unable to find script directory \"%s\"; should be in the base directory of the package" % (scriptdir))

    runnum = str(self.run_number)
    runrecord = self.record_directory + "/" + runnum

    cmds = setup_database_commands()

    cmds.append(" scriptdir=" + scriptdir)
    cmds.append( "tmpdir=$(uuidgen)")
    cmds.append( "mkdir $tmpdir" )
    cmds.append( "cd $tmpdir" )
    cmds.append( "cp -rp " + runrecord + " . ")
    cmds.append( "chmod 777 " + runnum )
    cmds.append( "cat " + runnum + "/metadata.txt | awk -f $scriptdir/fhiclize_metadata_file.awk > " + runnum + "/metadata_r" + runnum + ".fcl" )
    cmds.append("cp -p " + runnum + "/config.txt " + runnum + "/config_r" + runnum + ".fcl")
    cmds.append( "rm -f " + runnum + "/*.txt")
    cmds.append( "for file in " + runnum + "/*.*.fcl ; do mv $file $( echo $file | sed -r 's/\./_/g;s/_fcl/\.fcl/' ) ; done")
    cmds.append( "conftool.sh -o import_global_config -g %sR%s -v ver001 -s %s" % 
                 (self.config_for_run, runnum, runnum) )
    cmds.append( "cd ..")
    cmds.append( "if [[ -d $tmpdir ]]; then rm -rf $tmpdir ; fi ")

    cmd = self.construct_checked_command( cmds )

    execute_commands_and_throw_if_problem( [ cmd ] )

    return


def get_daqinterface_config_info_base(self, daqinterface_config_label):

    cmds = setup_database_commands()

    cmds.append( "conftool.sh -o export_global_config -g %s" % (daqinterface_config_label))

    execute_commands_and_throw_if_problem( cmds )

    fclfile = config_basedir() + "/newconfig/daqinterface_config/daqinterface_config.fcl"

    if not os.path.exists( fclfile ):
        raise Exception("Error in %s: unable to find expected DAQInterface configuration FHiCL document %s" % \
                            (get_daqinterface_config_info_base.__name__, fclfile))
    
    inf = open( fclfile )
    assert inf

    def parse_fhicl_sequence(keyname, line):
        res = re.search(r"^\s*" + keyname + "\s*:\s*\[(.*)\]", line)
        if res:
            vals_string = res.group(1)
            return [ val.strip() for val in vals_string.split(",") ]
        else:
            return []

    for line in inf.readlines():

        line = expand_environment_variable_in_string( line )

        # Is this line a comment?
        res = re.search(r"^\s*#", line)
        if res:
            continue

        res = re.search(r"\s*PMT_host\s*:\s*(\S+)", line)
        if res:
            self.pmt_host = res.group(1).strip("\"")
            continue

        res = re.search(r"\s*PMT_port\s*:\s*(\S+)", line)
        if res:
            self.pmt_port = res.group(1).strip("\"")
            continue

        res = re.search(r"\s*DAQ_directory\s*:\s*(\S+)",
                            line)
        if res:
            self.daq_dir = res.group(1).strip("\"")
            continue

        res = re.search(r"\s*debug_level\s*:\s*(\S+)",
                        line)
        if res:
            self.debug_level = int(res.group(1))
            continue
    
        seq = parse_fhicl_sequence("Eventbuilder_hosts", line)
        if len(seq) > 0:
            eventbuilder_hosts = seq
            continue

        seq = parse_fhicl_sequence("Eventbuilder_ports", line)
        if len(seq) > 0:
            eventbuilder_ports = seq
            continue

        seq = parse_fhicl_sequence("Aggregator_hosts", line)
        if len(seq) > 0:
            aggregator_hosts = seq
            continue

        seq = parse_fhicl_sequence("Aggregator_ports", line)
        if len(seq) > 0:
            aggregator_ports = seq
            continue

    for (host, port) in zip( eventbuilder_hosts, eventbuilder_ports):
        self.procinfos.append( self.Procinfo( "EventBuilder", host, port) )

    for (host, port) in zip( aggregator_hosts, aggregator_ports):
        self.procinfos.append( self.Procinfo( "Aggregator", host, port) )

    # Now that we've read in the parameters from the file obtained
    # from the database, move the file up a directory so it won't get
    # clobbered when the physics configuration is obtained - this way
    # we'll be able to save the file in the run record when the start
    # transition is issued

    newfclfile = string.replace(fclfile, "newconfig/", "")

    cmd = "mv %s %s" % (fclfile, newfclfile) 

    Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if not os.path.exists( newfclfile ):
        raise Exception("Problem executing the following command: \"%s\"" % (cmd))
    
    return newfclfile
