
import os
import sys
sys.path.append( os.environ["ARTDAQ_DAQINTERFACE_DIR"] )

import re
import subprocess
from subprocess import Popen

from time import sleep

from rc.control.utilities import execute_command_in_xterm
from rc.control.utilities import get_pids

def launch_art_procs_base(self, filename):

    if not os.path.exists(filename):
        raise Exception("Expected file \"%s\" meant to contain info on the art online monitoring processes does not exist")

    inf = open( filename )
    
    self.art_pids = []

    art_process_search_string = ":[0-9][0-9]\s*art -c"

    for line in inf.readlines():
        res = re.search(r"^\s*art\s*:\s*(\S+)", line)
        
        if res:

            art_pids_before = get_pids(art_process_search_string)

            num_art_attempts = 2

            cmds = []
            cmds.append(". %s" % (self.daq_setup_script))
            cmds.append("art -c %s" % (res.group(1)))
            
            # There will be max_checks*check_period seconds for the art
            # process to appear before an attempt is considered a
            # failure

            max_checks = 6
            check_period = 1

            for i_attempt in range(num_art_attempts):

                attempt_succeeded = False

                execute_command_in_xterm(os.environ["PWD"], \
                                             "; ".join(cmds))
                
                for i_check in range(max_checks):
                    art_pids_after = get_pids(art_process_search_string)

                    new_art_proc = list( set(art_pids_after) - set(art_pids_before) )

                    if len(new_art_proc) != 1:

                        if self.debug_level >= 2:
                            print "Check #%d unsuccessful, found %d new processes" % \
                                (i_check+1, len(new_art_proc))
                        sleep(check_period)
                    else:
                        self.art_pids.append( new_art_proc[0] )
                        attempt_succeeded = True
                        break
                
                if attempt_succeeded:
                    break
                else:
                    print "Attempt %d of %d: new art monitoring process did not appear as expected using FHiCL document %s" % (i_attempt+1, num_art_attempts, res.group(1))

    if self.debug_level >= 2:
        print "art_pids: "
        print self.art_pids

def kill_art_procs_base(self):

    art_xterm_pids = get_pids("xterm.*art -c")

    for art_xterm_pid in art_xterm_pids:
        cmd = "kill %s; sleep 2; kill -9 %s" % (art_xterm_pid, art_xterm_pid)
        Popen(cmd, shell=True, stdout=subprocess.PIPE,
              stderr=subprocess.STDOUT)

    self.art_pids = []

def main():
    
    test_launch_art_procs_base = True

    if test_launch_art_procs_base:

        class MockDAQInterface:
            daq_setup_script = "DEFINE_ME"
            debug_level = 3

        mockdaqint = MockDAQInterface()
        testfile = "/home/jcfree/artdaq-utilities-daqinterface/docs/boot.txt"


        print "Assuming DAQ setup script is %s, input file is %s" % \
            (mockdaqint.daq_setup_script, testfile)

        launch_art_procs_base( mockdaqint, testfile )
        

if __name__ == "__main__":
    main()
