
import subprocess
from subprocess import Popen

def get_config_info_base(self):

    # JCF, Nov-10-2016

    # The hardwired paths below are specific to pdunedaq01; these will
    # need to be changed on another system
    
    proddir = "/home/nfs/products"
    configbasedir = "/home/nfs/dunedaq/daqarea/config_protodune"

    cmds = []
    cmds.append( "cd %s" % (configbasedir) )
    cmds.append( ". %s/setup" % (proddir))
    cmds.append( "setup artdaq v1_13_02 -q e10:eth:prof:s35")
    cmds.append( "conftool.sh -o export_global_config -g demo1")

    cmd = " ; ".join( cmds )

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
