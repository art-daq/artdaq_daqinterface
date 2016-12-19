
import subprocess
from subprocess import Popen

import os

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


#### Need to work on code below

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
    cmds.append( "cat " + runnum + "/config.txt | awk -f $scriptdir/fhiclize_daqinterface_config_file.awk > " + runnum + "/config_r" + runnum + ".fcl" )
    cmds.append( "rm -f " + runnum + "/*.txt")
    cmds.append( "for file in " + runnum + "/*.*.fcl ; do mv $file $( echo $file | sed -r 's/\./_/g;s/_fcl/\.fcl/' ) ; done")
    cmds.append( "conftool.sh -o import_global_config -g %sR%s -v ver001 -s %s" % 
                 (self.config_for_run, runnum, runnum) )
    cmds.append( "cd ..")
    cmds.append( "if [[ -d $tmpdir ]]; then rm -rf $tmpdir ; fi ")

    cmd = self.construct_checked_command( cmds )

    execute_commands_and_throw_if_problem( [ cmd ] )

    return
