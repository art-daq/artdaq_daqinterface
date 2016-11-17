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


class NoisyExample(Component):
    """
    NoisyExample: A spewy example of a Component implementation

    This example extends the basic Component (rc/control/component.py)
    base class
    """
    __MAXPORT = 65535

    def __init__(self, logpath=None, name="toycomponent",
                 rpc_host="localhost", control_host='localhost',
                 synchronous=True, rpc_port=6660):

        print("Welcome to NoiseExample.__init__")
        # Call your base class __init__ function
        Component.__init__(self, logpath=logpath,
                           name=name,
                           rpc_host=rpc_host,
                           control_host=control_host,
                           synchronous=synchronous,
                           rpc_port=rpc_port,
                           skip_init=False)
        self.logger.log("Done init")
        self.last_time = datetime.datetime.utcnow()
        self.count = 0
        self.__do_config = False
        self.__do_start_run = False

    def runner(self):
        """
        Component "ops" loop.  Called at threading hearbeat frequency,
        currently 1/sec.

        We override this, and use it to check statuses, send the load,
        etc.

        """
        if self.__do_config:
            self.logger.log("Time to configure NoisyExample....30sec")
            self.logger.log("Config name: %s" % self.run_params["config"])
            self.logger.log("Selected DAQ comps: %s" %
                            self.run_params["daq_comp_list"])
            time.sleep(30)
            self.logger.log("Configuration complete")
            # Let RC know we're done with transition...
            self.complete_state_change(self.name, "initializing")
            self.__do_config = False
        if self.__do_start_run:
            self.logger.log("Time to start NoisyExample....60sec")
            self.logger.log("Run num: %s" % self.run_params["run_number"])
            time.sleep(60)
            self.logger.log("Run start complete")
            # Let RC know we're done with transition...
            self.complete_state_change(self.name, "starting")
            self.__do_start_run = False

        # Let's not overload the logfile...
        self.count += 1
        if (self.count % 10 != 0):
            return None
        self.logger.log("NoisyExample runner.")
        if self.state(self.name) == "running":
            # self.logger.log("NoisyExample is started.  Time to get uptime?")
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
                self.logger.log("NoisyExample run, found load %s" % load_now)
        if self.state(self.name) == "paused":
            self.logger.log("NoisyExample is paused.  No soup for you.")

    def start_running(self):
        self.logger.log("Starting noisy example")
        if (self.synchronous):
            self.logger.log("I am synchronous, I started with daq")
            self.logger.log("Started with Run %s" %
                            self.run_params['run_number'])

        if (not self.synchronous):
            self.logger.log("I am an asynchronous component, I stand alone")
        # can't do this yet, transition not fully complete
        # self.complete_state_change(self.name, "starting")
        # set flag to let runner know to configure..
        self.__do_start_run = True

    def initialize(self):
        """
        We override this to do something during "initializing"
        transitional state (changing from "stopped" to "ready" states)

        Here we get the configuration name from RC server
        """
        self.logger.log("Specified config: %s" %
                        self.run_params['config'])
        self.logger.log("NoisyExample Init!")
        # set flag to let runner know to configure..
        self.__do_config = True
        # can't do this yet, transition not fully complete
        # self.complete_state_change(self.name, "initializing")

    def stop_running(self):
        """
        We override this to explicitly do something during "stopping"
        transitional state (changing from "running" to "ready" states)
        """
        self.logger.log("Stopping noisy example")
        self.complete_state_change(self.name, "stopping")

    def pause_running(self):
        """
        We override this to explicitly do something during "pausing"
        transitional state (changing from "running" to "paused" states)
        """
        self.logger.log("Pausing noisy example")
        self.complete_state_change(self.name, "pausing")

    def resume_running(self):
        """
        Override this to explicitly do something during "resuming" transitional
        state (changing from "paused" to "running" states)
        """
        self.logger.log("Resuming noisy example")
        self.complete_state_change(self.name, "terminating")

    def terminate(self):
        """
        We override this to explicitly do something during "terminating"
        transitional state (changing from "ready" to "stopped" states)
        """
        self.logger.log("Terminating noisy example")
        self.complete_state_change(self.name, "terminating")

    def recover(self):
        """
        We override this to explicitly do something during
        "recovering" transitional state

        Perform resets, clean up file handles, etc.  Go back to
        a "clean stop" in the "stopped" state.
        """
        self.logger.log("Recovering noisy example")
        self.complete_state_change(self.name, "recovering")


def get_args():  # no-coverage
    parser = argparse.ArgumentParser(
        description="Simulated LBNE 35 ton component")
    parser.add_argument("-n", "--name", type=str, dest='name',
                        default="squawky", help="Component name")
    parser.add_argument("-r", "--rpc-port", type=int, dest='rpc_port',
                        default=6660, help="RPC port")
    parser.add_argument("-H", "--rpc-host", type=str, dest='rpc_host',
                        default='localhost', help="This hostname/IP addr")
    parser.add_argument("-c", "--control-host", type=str, dest='control_host',
                        default='localhost', help="Control host")
    parser.add_argument("-s", "--is-synchronous", dest="synchronous",
                        default=True, action="store_true",
                        help="Component is synchronous (starts/stops w/ DAQ)")
    return parser.parse_args()


def main():  # no-coverage
    """
    When not running `Component` under test, it can be instantiated on
    the command line using `lbnecomp` (`lbnecomp -h` for help).
    """
    args = get_args()
    with NoisyExample(logpath=os.path.join(os.environ["HOME"], ".lbnerc.log"),
                      **vars(args)):
        wait_for_interrupt()
