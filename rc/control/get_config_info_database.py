
import subprocess
from subprocess import Popen

import os

def get_config_info_base(self):

    configbasedir = os.environ["HOME"] + "/daqarea/work-db-dir"

    sourcemefile = os.environ["HOME"] + "/.database.bash.rc"

    if not os.path.exists( sourcemefile ):
        self.alert_and_recover("Error: required file to source for configuration \"%s\" doesn't appear to exist" %
                               (sourcemefile))

    cmds = []
    cmds.append( ". " + sourcemefile )
    cmds.append( "cd %s" % (configbasedir) )
    cmds.append( "conftool.sh -o export_global_config -g " + self.config_for_run)

    cmd = self.construct_checked_command( cmds )

    proc = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cfg_lines = proc.stdout.readlines()
    
    if len(cfg_lines) == 0:
        print "Error: No lines of output"
        self.alert_and_recover("Error: No lines of output from execution of the following: \"%s\"" % \
                                   (cmd) )
        return "", []

    if ( "Return status: succeed" in cfg_lines[-1]):
        configdir = "%s/newconfig/" % (configbasedir)
        return configdir, [ configdir ]
    else:
        print "Error, the output from get_config_info was \"%s\"" % ("".join( cfg_lines ))
        self.alert_and_recover("Error: execution of the following \"%s\" resulted in "
                               "the following output: \"%s\"" % (cmd, "".join( cfg_lines )))
        return "", []
