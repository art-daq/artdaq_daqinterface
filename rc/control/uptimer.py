import argparse
import datetime
from re import search
import time
import os
import random
from rc.log import Logger
from rc.io import sender
from rc.io.rpc import rpc_server
from rc.threading import threadable
from rc.util.contexts import ContextObject
from rc.util import wait_for_interrupt
from rc.control.component import Component, announcing_sender


class Uptimer(Component):
    """
    Uptimer: A basic example of a Component implementation

    This example extends the basic Component (rc/control/component.py)
    base class
    """
    __MAXPORT = 65535

    def __init__(self, logpath=None, name="toycomponent",
                 rpc_host="localhost", control_host='localhost',
                 synchronous=False, rpc_port=6659):

        Component.__init__(self, logpath=logpath,
                           name=name,
                           rpc_host=rpc_host,
                           control_host=control_host,
                           synchronous=synchronous,
                           rpc_port=rpc_port,
                           skip_init=True)
        self.last_time = datetime.datetime.utcnow()

    def runner(self):
        if self.state(self.name) == "running":
            tnow = datetime.datetime.utcnow()
            if (tnow - self.last_time).seconds > 60:
                self.last_time = tnow
                upstr = os.popen('uptime').read().rstrip()
                match = search('load ave.+?: ([0-9\.]+)', upstr)
                load_now = match.group(1)
                self.sender.send({"type": "moni",
                                  "service": self.name,
                                  "t": str(tnow),
                                  "varname": "cpuload",
                                  "value": float(load_now)})
                self.logger.log("Uptimer run, found load %s" % load_now)


def get_args():  # no-coverage
    parser = argparse.ArgumentParser(
        description="Simulated LBNE 35 ton component")
    parser.add_argument("-n", "--name", type=str, dest='name',
                        default="uptime", help="Component name")
    parser.add_argument("-r", "--rpc-port", type=int, dest='rpc_port',
                        default=6659, help="RPC port")
    parser.add_argument("-H", "--rpc-host", type=str, dest='rpc_host',
                        default='localhost', help="This hostname/IP addr")
    parser.add_argument("-c", "--control-host", type=str, dest='control_host',
                        default='localhost', help="Control host")
    parser.add_argument("-s", "--is-synchronous", dest="synchronous",
                        default=False, action="store_true",
                        help="Component is synchronous (starts/stops w/ DAQ)")
    return parser.parse_args()


def main():  # no-coverage
    """
    When not running `Component` under test, it can be instantiated on
    the command line using `lbnecomp` (`lbnecomp -h` for help).
    """
    args = get_args()
    with Uptimer(logpath=os.path.join(os.environ["HOME"], ".lbnerc.log"),
                 **vars(args)):
        wait_for_interrupt()
