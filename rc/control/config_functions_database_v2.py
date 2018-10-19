# JCF, Apr-20-2017

# For this module to work, you'll first need to have set up the
# artdaq-database in the shell environment

import os
import sys
sys.path.append( os.environ["ARTDAQ_DAQINTERFACE_DIR"] )

dbdirs = [dbdir for dbdir in os.environ["PYTHONPATH"].split(":") if "/artdaq_database/" in dbdir]
assert len(dbdirs) == 1, "More than one path in $PYTHONPATH appears to be an artdaq-database path"
sys.path.append(dbdirs[0] + "/../bin")

import subprocess
from subprocess import Popen
from rc.control.deepsuppression import deepsuppression
from rc.control.utilities import make_paragraph

import re
import os
import string
import shutil

from rc.control.utilities import expand_environment_variable_in_string
from conftool import exportConfiguration
from conftool import getListOfAvailableRunConfigurationPrefixes
from conftool import getListOfAvailableRunConfigurations
from conftool import archiveRunConfiguration

def config_basedir(self):
    return "/tmp/database/"

def get_config_info_base(self):

    basedir = os.getcwd()

    uuidgen=Popen("uuidgen", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip()
    config_dir = config_basedir(self) + uuidgen

    Popen("mkdir -p %s" % config_dir, shell=True).wait()
    os.chdir( config_dir )

    with deepsuppression(self.debug_level < 2):
        result = exportConfiguration( self.config_for_run )

    if not result:
        raise Exception("Error: the exportConfiguration function with the argument \"%s\" returned False" % \
                        self.config_for_run)

    # JCF, Nov-22-2017

    # Disabled the common code logic for the time being; plan is to
    # reinstate it when there's time to modify the protoDUNE FHiCL
    # configurations to adhere to it

    if False:
        if os.path.exists("common_code"):
            raise Exception("Error: the requested configuration \"%s\" contains a subdirectory called \"common_code\" (see directory %s); this should not be the case, as \"common_code\" needs to be a separate configuration" % (self.config_for_run, os.getcwd()))

        common_code_configs = getListOfAvailableRunConfigurations("common_code")

        if len(common_code_configs) == 0:
            raise Exception("Error: unable to find any common_code configurations in the database")

        common_code_configs.sort()
        common_code_config = common_code_configs[-1]

        result = exportConfiguration( common_code_config )
        if not result:
            raise Exception("Error: the \"%s\" set of FHiCL documents doesn't appear to be retrievable from the database" % (common_code_config))

    os.chdir(basedir)
    
    return config_dir, [fhicl_dir for fhicl_dir, dummy, dummy in os.walk(config_dir)]


def put_config_info_base(self):

    scriptdir = os.environ["ARTDAQ_DAQINTERFACE_DIR"] + "/utils"

    if not os.path.exists( scriptdir ):
        raise Exception("Error in %s: unable to find script directory \"%s\"; should be in the base directory of the package" % (put_config_info_base.__name__, scriptdir))

    runnum = str(self.run_number)
    runrecord = self.record_directory + "/" + runnum

    tmpdir = "/tmp/" + Popen("uuidgen", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip()

    cmds = []
    cmds.append(" scriptdir=" + scriptdir)
    cmds.append( "mkdir " + tmpdir)
    cmds.append( "cd " + tmpdir)
    cmds.append( "cp -rp " + runrecord + " . ")
    cmds.append( "chmod 777 " + runnum )
    cmds.append( "cat " + runnum + "/metadata.txt | awk -f $scriptdir/fhiclize_metadata_file.awk > " + runnum + "/metadata.fcl" )
    cmds.append( "cat " + runnum + "/boot.txt | awk -f $scriptdir/fhiclize_boot_file.awk > " + runnum + "/boot.fcl" )
    cmds.append( "cat " + runnum + "/known_boardreaders_list.txt | sed -r 's/^\s*(\S+)\s+(\S+)\s+(\S+)/\\1: [\"\\2\", \"\\3\"]/' > " + runnum + "/known_boardreaders_list.fcl")
    cmds.append( "rm -f " + runnum + "/*.txt")

    if os.getenv("ARTDAQ_DATABASE_CONFDIR") is None:
        raise Exception(make_paragraph("Environment variable ARTDAQ_DATABASE_CONFDIR needs to be set in order for DAQInterface to determine where to find the schema.fcl file needed to archive configurations to the database; since ARTDAQ_DATABASE_CONFDIR is not set this may indicate that the version of artdaq_database you're using is old"))

    cmds.append("cp -p %s/schema.fcl ." % os.environ["ARTDAQ_DATABASE_CONFDIR"])

    status = Popen( "; ".join( cmds ), shell=True).wait()

    for filename in [tmpdir, "%s/%s" % (tmpdir, runnum), "%s/%s/metadata.fcl" % (tmpdir, runnum)] :
        assert os.path.exists( filename ), "%s is unexpectedly missing" % (filename)

    if status != 0:
        raise Exception("Problem during execution of the following:\n %s" % "\n".join(cmds))

    with open( "%s/%s/DataflowConfiguration.fcl" % (tmpdir, runnum), "w" ) as dataflow_file:

        with open( "%s/%s/boot.fcl" % (tmpdir, runnum) ) as boot_file:
            for line in boot_file.readlines():
                
                ignore_line = False

                for procname in ["EventBuilder", "DataLogger", "Dispatcher", "RoutingMaster"] :
                    res = re.search(r"^\s*%s_" % (procname), line)
                    if res:
                        ignore_line = True
                        break

                if "debug_level" in line or line == "":
                    ignore_line = True

                if not ignore_line:
                    dataflow_file.write("\n" + line)

        proc_attrs = ["host", "port", "label", "rank"]
        proc_types = ["BoardReader", "EventBuilder", "DataLogger", "Dispatcher", "RoutingMaster"]

        proc_line = {}

        with open("%s/ranks.txt" % (runrecord)) as ranksfile:
            for line in ranksfile.readlines():
                res = re.search(r"^\s*(\S+)\s+([0-9]+)\s+(\S+)\s+([0-9]+)\s*$", line)
                if res:
                    host, port, label, rank = res.group(1), res.group(2), res.group(3), res.group(4)
                    
                    for procinfo in self.procinfos:
                        if label == procinfo.label:
                            assert host == procinfo.host
                            assert port == procinfo.port

                            # "host" used for the check, but could just as well be "port", "label" or "rank"
                            if "%s_host" % (procinfo.name) not in proc_line.keys():
                                for proc_attr in proc_attrs:
                                    proc_line["%s_%s" % (procinfo.name, proc_attr)] = "%s_%ss: [" % (procinfo.name, proc_attr)
                            
                            proc_line["%s_host" % (procinfo.name)] += "\"%s\"," % (procinfo.host)
                            proc_line["%s_port" % (procinfo.name)] += "\"%s\"," % (procinfo.port)
                            proc_line["%s_label" % (procinfo.name)] += "\"%s\"," % (procinfo.label)
                            proc_line["%s_rank" % (procinfo.name)] += "\"%s\"," % (rank)

        for proc_line_key, proc_line_value in proc_line.items():
            proc_line_value = proc_line_value[:-1] # Strip the trailing comma
            proc_line[ proc_line_key ] = proc_line_value + "]"
            dataflow_file.write("\n" + proc_line[ proc_line_key ] )

        with open( "%s/%s/metadata.fcl" % (tmpdir, runnum) ) as metadata_file:
            for line in metadata_file.readlines():
                if "Start_time" not in line and "Stop_time" not in line and not line == "":
                    dataflow_file.write("\n" + line)

    with open( "%s/%s/RunHistory.fcl" % (tmpdir, runnum), "w" ) as runhistory_file:
        runhistory_file.write("\nrun_number: %s" % (runnum))
        

    basedir=os.getcwd()
    os.chdir( tmpdir )

    with deepsuppression(self.debug_level < 2):
        result = archiveRunConfiguration( self.config_for_run, runnum )

    if not result:
        raise Exception(make_paragraph("There was an error attempting to archive the FHiCL documents (temporarily saved in %s); this may be because of an issue with the schema file, %s/schema.fcl, such as an unlisted fragment generator" % (tmpdir, os.environ["ARTDAQ_DATABASE_CONFDIR"])))

    os.chdir( basedir )

    res = re.search(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", tmpdir)
    assert res, "Unable to find uuidgen-generated temporary directory, will perform no deletions"

    shutil.rmtree( tmpdir )

    return

def listdaqcomps_base(self):
    assert False, "%s not yet implemented" % (listdaqcomps_base.__name__)

def listconfigs_base(self):
    print
    print "Available configurations: "

    config_cntr = 0

    with open("/tmp/listconfigs_" + os.environ["USER"] + ".txt", "w") as outf:
        for config in getListOfAvailableRunConfigurations():
            config_cntr += 1

            if config_cntr <= self.max_configurations_to_list:
                outf.write(config + "\n")
                print config

def main():

    listconfigs_test = False
    get_config_info_test = False
    put_config_info_test = False

    if listconfigs_test:
        print "Calling listconfigs_base"
        listconfigs_base("ignored_argument")
        
    if get_config_info_test:
        print "Calling get_config_info_base"

        class MockDAQInterface:
            config_for_run = "push_pull_testing"

        mydir, mydirs = get_config_info_base( MockDAQInterface() )

        print "FHiCL directories to search: " + " ".join(mydirs)
        print "Directory where the FHiCL documents are located: " + mydir

    if put_config_info_test:
        print "Calling put_config_info_base"

        class MockDAQInterface:
            run_number = 73
            record_directory = "/daq/artdaq/run_records/"
            config_for_run = "push_pull_testing"

        put_config_info_base( MockDAQInterface() )

if __name__ == "__main__":
    main()
