import subprocess
from subprocess import Popen

import re
import os
import string

import sys
sys.path.append( os.getcwd() )
sys.path.append(os.environ["PYTHONPATH"] + "/../bin/")

from rc.control.utilities import expand_environment_variable_in_string
from conftool import exportConfiguration

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
    assert False, "%s not yet implemented" % (put_config_info_base.__name__)

def listdaqcomps_base(self):
    assert False, "%s not yet implemented" % (listdaqcomps_base.__name__)

def listconfigs_base(self):
    assert False, "%s not yet implemented" % (listconfigs_base.__name__)

def main():

    listconfigs_test = False
    get_config_info_test = True

    if listconfigs_test:
        print "Calling listconfigs_base"
        listconfigs_base("ignored_argument")
        
    if get_config_info_test:
        print "Calling get_config_info_base"

        class MockDAQInterface:
            config_for_run = "smurf"

        mydir, mydirs = get_config_info_base( MockDAQInterface() )

        print "FHiCL directories to search: " + " ".join(mydirs)
        print "Directory where the FHiCL documents are located: " + mydir

        
if __name__ == "__main__":
    main()

