"""
lbnecmd: Command line interface to LBNE Run Control (prototype)

Usage: `lbnecmd <cmd>`

Valid commands:

.. code-block:: bash

     help             # This message
     launch <dbserv>  # Start lbnecontrol

     check            # Get status report from lbnecontrol
     check <comp>     # Check status of <comp>
     control <service> <host> <port> <syncasync>
                      # Establish control of <service> at <host>:<port>.
                      # <syncasync> is "synchronous" for DAQ-like components,
                      # "asynchronous" for stand-alone components.
     ignore <service> # Undo control of <service>
     start <service>  # Start stand-alone component (ready -> running)
     stop <service>   # Stop stand-alone service (running -> ready)
     init <service>   # Initialize a service (stopped -> ready)
     terminate <service>
                      # Terminate a service (ready -> stopped)
     pause <service>  # Pause a service (running -> paused)
     resume <service> # Resume a service (paused -> running)
     listconfigs      # Get a list of valid configs from Config Mgr
     setconfig <cfg>  # Set the configuration name for upcoming run
     listdaqcomps     # Get a list of available DAQ components
                      # available are read, one-per-line
                      # from ~/.lbnerc-components
     setdaqcomps <list>
                      # Set the requested DAQ compoents for use
     adddaqcomps <list>
                      # Add the requested DAQ compoents for use
     rmdaqcomps <list>
                      # Remove the requested DAQ compoents from list for use
     listruntype      # Show current selected run type
     setruntype       # Select run type for run, available types:
                      # Test - test runs (default)
                      # Physics - High quality physics data taking
                      # Commissioning - Engineering checkout runs
                      # Calibration - Detector calibration data
     kill             # Kill lbnecontrol

     Use <service> "daq" to control all synchronous DAQ components at once.
"""

from __future__ import print_function
from .processes import (control_running, start_control, kill_control,
                        control_pid_file)
from rc.io.rpc import rpc_client
from rc.util.confirm import confirm
from socket import error as socketerror
import os
import sys
import argparse
import datetime
import psycopg2
import xmlrpclib
import socket


def call_rpc_function(name, args):
    with rpc_client() as c:
        return getattr(c, name)(args)


def launch(*args):  # no-coverage
    if not control_running():
        start_control(args)
    else:
        print("Control program is running or stale process file (%s) exists!" %
              control_pid_file())


def kill():  # no-coverage
    if control_running():
        kill_control()


def tail():  # no-coverage
    os.system("tail -f ~/.lbnerc.log | lbnelog")


def help():
    return sys.modules[__name__].__doc__.rstrip()


def listruntype(*args):
    res = call_rpc_function("listruntype", args)
    ret = []
    ret.append(res)
    return "\n".join(ret)


def setruntype(*args):
    res = call_rpc_function("setruntype", args)
    if res["succeeded"]:
        return "OK"
    else:
        return res["reason"]


def listconfigs(*args):
    res, current_config = call_rpc_function("listconfigs", args)
    ret = []
    # They come pre-sorted
    ret.append("Available configs (Name : description)\n")
    for config in res:
        ret.append("%s : %s" %
                   (config["config_label"], config["config_desc"]))
    ret.append("\nCurrent selected config: %s" % current_config)
    return "\n".join(ret)


def setconfig(*args):
    res = call_rpc_function("setconfig", args)
    if res["succeeded"]:
        return "OK"
    else:
        return res["reason"]


def listdaqcomps(*args):
    res = call_rpc_function("listdaqcomps", args)
    ret = []
    for item in res:
        ret.append(str(item))
    return "\n".join(ret)


def setdaqcomps(*args):
    res = call_rpc_function("setdaqcomps", args)
    if res["succeeded"]:
        return "OK"
    else:
        return res["reason"]

def adddaqcomps(*args):
    res = call_rpc_function("adddaqcomps", args)
    if res["succeeded"]:
        return "OK"
    else:
        return res["reason"]

def rmdaqcomps(*args):
    res = call_rpc_function("rmdaqcomps", args)
    if res["succeeded"]:
        return "OK"
    else:
        return res["reason"]

def getsettings(*args):
    res = call_rpc_function("getsettings", args)
    ret = []
    ret.append("DAQ config")
    ret.append("**********")
    ret.append("Run Type: %s" % res["run_params"]["run_type"])
    ret.append("Selected config: %s" % res["run_params"]["config"])
    ret.append("Selected DAQ components:")
    for item in sorted(res["run_params"]["daq_comp_list"]):
        ostring = ("   " + item + " (" +
                   res["run_params"]["daq_comp_list"][item][0] +
                   ":" + res["run_params"]["daq_comp_list"][item][1] +
                   ")")
        ret.append(ostring)
    return "\n".join(ret)


def ignore(*args):
    res = call_rpc_function("ignore", args)
    if res["succeeded"]:
        return "OK"
    else:
        assert res["reason"] == "not_found"
        return ("Component %s is not in the list of currently "
                "controlled components" % args[0])


def check(*args):
    res = call_rpc_function("check", args)
    if not res["succeeded"]:
        return res["reason"]
    tdu_conn = xmlrpclib.ServerProxy("http://lbnedaq1:50008/RPC2")
    try:
        tdu_call = tdu_conn.system.listMethods()
        tdu_check = True
    except socket.error as v:
        tdu_check = False
    ret = []
    # ret.append(str(res))
    if not args:
        givelink = False
        ret.append("lbnecontrol: Available")
        if res["cfgmgrok"]:
            ret.append("CfgMgr: Available")
        else:
            ret.append("CfgMgr: **Not Found**")
            givelink = True
        daqintst = "DAQInterface: **Not Found**"
        for compie in res["components"]:
            if (compie["name"] == "daqint" and
                    compie["state"] != "missing"):
                daqintst = "DAQInterface: Available"
        ret.append(daqintst)
        if tdu_check:
            ret.append("TDUControl: Available")
        else:
            ret.append("TDUControl: **Not Found**")
        #ret.append("TDUControl:  please check with check_daq_applications.sh")
        ret.append("")
        for elem in ret:
            if "*Not Found*" in elem:
                ret.append("Please see the wiki for guidance on"
                           " missing components:")
                ret.append("https://cdcvs.fnal.gov/redmine/"
                           "projects/lbne-daq/wiki/Running_DAQ_Interface")
                ret.append("")
                break
    if "run_params" in res:
        ret.append("Run number: %d\nRun configuration: %s\n"
                   "Run type: %s" %
                   (res["run_params"]["run_number"],
                    res["run_params"]["config"],
                    res["run_params"]["run_type"]))

    def cstr(c):
        return ("%s@%s:%s (%s): %s" %
                (c["name"], c["host"], c["port"],
                 "synchronous" if c["synchronous"] else "asynchronous",
                 c["state"]))

    return "\n".join(ret + map(cstr, res["components"]))


def control_verb(verb, args):
    res = call_rpc_function(verb, args)
    if not res["succeeded"]:
        return res["reason"]
    return "OK"


def start(*args):
    if "daq" in args:
        check_str = getsettings(args)
        print(check_str)
        oktogo = confirm(prompt="Start DAQ with these settings?",
                         resp=True)
        if oktogo:
            return control_verb("start", args)
        else:
            return "Abort"
    else:
        return control_verb("start", args)


def stop(*args):
    return control_verb("stop", args)


def pause(*args):
    return control_verb("pause", args)


def resume(*args):
    return control_verb("resume", args)


def init(*args):
    return control_verb("initialize", args)


def terminate(*args):
    return control_verb("terminate", args)


def control(*args):
    return control_verb("control", args)


def dispatch(cmdline_args):
    cmd, args = cmdline_args[0], cmdline_args[1:]
    try:
        return getattr(sys.modules[__name__], cmd)(*args)
    except AttributeError:
        return "Unknown command"
    except socketerror as msg:
        return "%s failed: '%s'.  Is lbnecontrol running?" % (cmd, msg)
    except Exception, e:  # no-coverage
        return "Unknown exception '%s'" % str(e)


def lbnecmd(argstring):
    args = argstring.split()
    return dispatch(args)


def main():  # no-coverage
    parser = argparse.ArgumentParser(
        epilog='"lbnecmd help" for a list of valid commands.')
    parser.add_argument("cmd", metavar='cmd', type=str, nargs='+',
                        help="One or more commands to lbnecontrol.")
    args = parser.parse_args()

    ret = dispatch(vars(args)["cmd"])
    if ret:
        print(ret)
