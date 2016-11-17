
import subprocess
from subprocess import Popen

def put_config_info_base(self):

    # JCF, Nov-11-2016

    # The hardwired paths below are specific to pdunedaq01; these will
    # need to be changed on another system
    
    proddir = "/home/nfs/products"
    configbasedir = "/home/nfs/dunedaq/daqarea/config_protodune"
    runnum = str(self.run_params["run_number"])
    runrecord = self.record_directory + "/" + runnum
    

    cmds = []
    cmds.append(" scriptdir=$PWD/utils")
    cmds.append( "cd %s" % (configbasedir) )
    cmds.append( ". %s/setup" % (proddir))
    cmds.append( "setup artdaq v1_13_02 -q e10:eth:prof:s35")
    cmds.append( "tmpdir=$(uuidgen)")
    cmds.append( "mkdir $tmpdir" )
    cmds.append( "cd $tmpdir" )
    cmds.append( "cp -rp " + runrecord + " . ")
    cmds.append( "chmod 777 " + runnum )
    cmds.append( "cat " + runnum + "/metadata_r" + runnum + ".txt | awk -f $scriptdir/fhiclize_metadata_file.awk > " + runnum + "/metadata_r" + runnum + ".fcl" )
    cmds.append( "cat " + runnum + "/config_r" + runnum + ".txt | awk -f $scriptdir/fhiclize_daqinterface_config_file.awk > " + runnum + "/config_r" + runnum + ".fcl" )
    cmds.append( "rm -f " + runnum + "/*.txt")
    cmds.append( "for file in " + runnum + "/* ; do mv $file $( echo $file | sed -r 's/\./_/g;s/_fcl/\.fcl/' ) ; done")
    cmds.append( "conftool.sh -o import_global_config -g demo1R%s -v ver001 -s %s" % 
                 (runnum, runnum) )
    cmds.append( "cd ..")
    cmds.append( "rm -rf $tmpdir ")

    cmd = " ; ".join( cmds )

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
