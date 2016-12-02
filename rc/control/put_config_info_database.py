
import subprocess
from subprocess import Popen

import os

def put_config_info_base(self):

    configbasedir = os.environ["HOME"] + "/daqarea/work-db-dir"

    sourcemefile = os.environ["HOME"] + "/.database.bash.rc"

    if not os.path.exists( sourcemefile ):
        self.alert_and_recover("Error: required file to source for configuration \"%s\" doesn't appear to exist" %
                               (sourcemefile))


    scriptdir = os.environ["PWD"] + "/utils"

    if not os.path.exists( scriptdir ):
        self.alert_and_recover("Error: unable to find script directory \"%s\"; should be in the base directory of the package" % (scriptdir))

    runnum = str(self.run_number_for_run)
    runrecord = self.record_directory + "/" + runnum


    cmds = []
    cmds.append(" scriptdir=" + scriptdir)
    cmds.append( ". " + sourcemefile )
    cmds.append( "cd %s" % (configbasedir) )
    cmds.append( "tmpdir=$(uuidgen)")
    cmds.append( "mkdir $tmpdir" )
    cmds.append( "cd $tmpdir" )
    cmds.append( "cp -rp " + runrecord + " . ")
    cmds.append( "chmod 777 " + runnum )
    cmds.append( "cat " + runnum + "/metadata.txt | awk -f $scriptdir/fhiclize_metadata_file.awk > " + runnum + "/metadata_r" + runnum + ".fcl" )
    cmds.append( "cat " + runnum + "/config.txt | awk -f $scriptdir/fhiclize_daqinterface_config_file.awk > " + runnum + "/config_r" + runnum + ".fcl" )
    cmds.append( "rm -f " + runnum + "/*.txt")
    cmds.append( "for file in " + runnum + "/*.*.fcl ; do mv $file $( echo $file | sed -r 's/\./_/g;s/_fcl/\.fcl/' ) ; done")
    cmds.append( "conftool.sh -o import_global_config -g %sR%s -v ver001 -s %s" % 
                 (self.config_for_run, runnum, runnum) )
    cmds.append( "cd ..")
    cmds.append( "rm -rf $tmpdir ")

    cmd = self.construct_checked_command( cmds )

    proc = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    cfg_lines = proc.stdout.readlines()
    
    if len(cfg_lines) == 0:
        print "Error: No lines of output"
        self.alert_and_recover("Error: No lines of output from execution of the following: \"%s\"" % \
                                   (cmd) )
        return

    if ( "Return status: succeed" in cfg_lines[-1]):
        return
    else:
        print "Error, the output from put_config_info was \"%s\"" % ("".join( cfg_lines ))
        self.alert_and_recover("Error: execution of the following \"%s\" resulted in "
                               "the following output: \"%s\"" % (cmd, "".join( cfg_lines )))
        return

    return
