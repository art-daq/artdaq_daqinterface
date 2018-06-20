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

    with deepsuppression():
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


    basedir=os.getcwd()
    os.chdir( tmpdir )

    with deepsuppression():
        archiveRunConfiguration( self.config_for_run, runnum )

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

    with open("/tmp/listconfigs_" + os.environ["USER"] + ".txt", "w") as outf:
        for config in getListOfAvailableRunConfigurations():
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
