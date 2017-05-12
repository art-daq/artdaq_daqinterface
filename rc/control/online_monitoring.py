
import os
import re

import subprocess
from subprocess import Popen

import sys
sys.path.append( os.getcwd() )

from rc.control.utilities import execute_command_in_xterm
from rc.control.utilities import get_pids

def launch_art_procs_base(self, filename):

    if not os.path.exists(filename):
        raise Exception("Expected file \"%s\" meant to contain info on the art online monitoring processes does not exist")

    inf = open( filename )
    
    self.art_pids = []

    for line in inf.readlines():
        res = re.search(r"^\s*art\s*:\s*(\S+)", line)
        
        if res:
            art_pids_before = get_pids("art -c")

            execute_command_in_xterm(os.environ["PWD"], \
                                         "cd %s; . %s ; art -c %s" % \
                                         (self.daq_dir, self.daq_setup_script, res.group(1)))

            art_pids_after = get_pids("art -c")
            
            new_art_proc = list( set(art_pids_after) - set(art_pids_before) )

            assert len(new_art_proc) == 1, "Failure in logic for finding art process ID"
            
            self.art_pids.append( new_art_proc[0] )

    if self.debug_level > 1:
        print "art_pids: "
        print self.art_pids

def kill_art_procs_base(self):
    for pid in self.art_pids:
        Popen("kill %s" % pid, shell = True)

    self.art_pids = []
