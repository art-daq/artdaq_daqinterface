# JCF, Apr-20-2017

# For this module to work, you'll first need to have set up the
# artdaq-database in the shell environment

import subprocess
from subprocess import Popen

import re
import os
import string
import shutil

import sys
sys.path.append( os.getcwd() )
sys.path.append(os.environ["PYTHONPATH"] + "/../bin/")

from rc.control.utilities import expand_environment_variable_in_string
from conftool import exportConfiguration
from conftool import getListOfAvailableRunConfigurationPrefixes
from conftool import getListOfAvailableRunConfigurations
from conftool import archiveRunConfiguration

def config_basedir(self):
    return "/daq/database/tmp/%s" % (self.config_for_run)

def get_config_info_base(self):

    basedir = os.getcwd()

    Popen("mkdir -p %s" % config_basedir(self), shell=True).wait()
    os.chdir( config_basedir(self) )
    result = exportConfiguration( self.config_for_run )

    if not result:
        raise Exception("Error: the exportConfiguration function with the argument \"%s\" returned False" % \
                        self.config_for_run)

    os.chdir(basedir)
    
    return config_basedir(self), [fhicl_dir for fhicl_dir, dummy, dummy in os.walk(config_basedir(self))]


def put_config_info_base(self):

    scriptdir = os.environ["PWD"] + "/utils"

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
    cmds.append( "rm -f " + runnum + "/*.txt")
    cmds.append("cp -p %s/conf/schema.fcl ." % os.environ["ARTDAQ_DATABASE_FQ_DIR"])
    
    status = Popen( "; ".join( cmds ), shell=True).wait()

    for filename in [tmpdir, "%s/%s" % (tmpdir, runnum), "%s/%s/metadata.fcl" % (tmpdir, runnum)] :
        assert os.path.exists( filename ), "%s is unexpectedly missing" % (filename)

    if status != 0:
        raise Exception("Problem during execution of the following:\n %s" % "\n".join(cmds))


    basedir=os.getcwd()
    os.chdir( tmpdir )
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
