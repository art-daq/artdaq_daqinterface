
import traceback
import os

from rc.control.deepsuppression import deepsuppression

def attempt_lcm_pulse(self, start_or_stop):
#def attempt_lcm_pulse(start_or_stop):

    print "INSIDE attempt_lcm_pulse, self.config_dirname = %s, self.run_params[\"config\"] = %s" % (self.config_dirname, self.run_params["config"])

    conf_file = "%s/%s/lcm_%s.conf" % (self.config_dirname,
                                          self.run_params["config"],
                                          start_or_stop)
                                         
    if not os.path.exists(conf_file):
        raise Exception("Error in DAQInterface::attempt_lcm_pulse : " + 
                        "unknown lcm configuration file \"%s\"" % (conf_file))

    cmds = []

    # See launch_procs() for info on this string jujitsu
    
    if self.lbneartdaq_build_dir[-1] == "/":
        setupdir = "/".join(self.lbneartdaq_build_dir.split("/")[0:-2])
    else:
        setupdir = "/".join(self.lbneartdaq_build_dir.split("/")[0:-1])

    cmds.append("cd " + self.lbneartdaq_build_dir)
    cmds.append("source " + setupdir + "/setupLBNEARTDAQ " +
                self.lbneartdaq_build_dir)


    cmds.append("cd /data/lbnedaq/lcmControl")
    cmds.append("source setup.sh")
    cmds.append("./bin/lcmControl.exe %s" % (conf_file))

    if self.debug_level >= 1:
        print
        print "About to call lcmControl.exe ; no warning message below this will imply success..."

    with deepsuppression():
        status = Popen("ssh lbnedaq1 ' " + ";".join(cmds) + " ' ", shell=True).wait()

    if status != 0:
        self.print_log("Warning in DAQInterface::attempt_lcm_pulse : " +
                       "error status code returned by lcmControl.exe call")
        
    print

    return


# JCF, 2/6/15

# attempt_sync_pulse() will send a sync pulse to the TDU via an
# XML-RPC server connection assuming the port of the XML-RPC
# server to the TDU is set to a non-negative integer. For more on
# the TDU and its code, take a look at Tom Dealtry's notes at
# https://cdcvs.fnal.gov/redmine/projects/lbne-daq/wiki/Starting_and_using_TDUControl

def attempt_sync_pulse(self):

    if int(self.tdu_xmlrpc_port) <= 0:
        self.print_log("XML-RPC server port for the TDU is set to <= 0;" +
                       " skipping sync pulse")
        return

    if os.getcwd().split("/")[-1] != "lbnerc":
        raise Exception("Exception in DAQInterface: " +
                        "expected to be in lbnerc/ directory")

    # JCF, 2/7/15 -- should I add a "ping" before sending the sync pulse?

    tdu_attempts = 5

    # JCF, Jan-25-2016

    # Due to the reconfiguration of the network this morning
    # performed by Geoff Savage, Tim Nicholls and Bonnie King, I'm
    # now launching the tdu_control_via_xmlrpcserver.py script
    # remotely on lbnedaq1

    cmd = "ssh lbnedaq1 'cd /data/lbnedaq/daqarea ; . fireup ; " + \
        "python rc/tdu/testing_scripts/tdu_control_via_xmlrpcserver.py " + \
        "-T 10.226.8.18 -p %s -s'" % (self.tdu_xmlrpc_port)

    for tdu_attempt in range(tdu_attempts):
        result = Popen(cmd, shell=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)

        lines = result.stdout.readlines()

        if lines[-1].strip() == "0 (SUCCESS)":
            print "TDU RESULT: " + lines[-1]
            break
        else:
            for line in lines:
                print line

    if not (lines[-1].strip() == "0 (SUCCESS)"):
        raise Exception("Exception in DAQInterface:" +
                        " problem running the" +
                        " tdu_control_via_xmlrpcserver.py script")

def start_datataking_base(self):

    try:
        attempt_lcm_pulse(self, "start")
    except Exception:
        self.print_log("DAQInterface caught an exception " +
                       "in do_start_running()")
        self.print_log(traceback.format_exc())

        self.alert_and_recover("An exception was "
                               "thrown during the start transition")
        return

    try:
        attempt_sync_pulse(self)
    except Exception:
        self.print_log("DAQInterface caught an exception " +
                       "in do_start_running()")
        self.print_log(traceback.format_exc())

        self.alert_and_recover("An exception was "
                               "thrown during the start transition")
        return
