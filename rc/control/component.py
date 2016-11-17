import argparse
import datetime
import os.path
import os
import random
#from toolz import assoc
from contextlib import contextmanager
#from rc.log import Logger
#from rc.io import sender
from rc.io.rpc import rpc_server
from rc.threading import threadable
from rc.util.contexts import ContextObject
from rc.util import wait_for_interrupt


# @contextmanager
# def announcing_sender(name, rpc_host, rpc_port, synchronous,
#                       control_host='localhost', control_port=5000):
#     with sender(ip=control_host, port=control_port) as s:
#         s.send({"type": "control",
#                 "name": name,
#                 "synchronous": synchronous,
#                 "host": rpc_host,
#                 "port": rpc_port})
#         yield s


class Component(ContextObject):
    """
    Dummy (or subclass-able) component for use with the LBNE Run
    Control protoype.
    """
    __MAXPORT = 65535

    def __init__(self, logpath=None, name="toycomponent",
                 rpc_host="localhost", control_host='localhost',
                 synchronous=False, rpc_port=6659, skip_init=False):
        if rpc_port > Component.__MAXPORT:
            raise ValueError("Maximum allowed port is %s" %
                             Component.__MAXPORT)
        if name == "daq":
            raise ValueError("Name 'daq' is not allowed for individual "
                             "components")
        self.name = name
        self.synchronous = synchronous
#        self.logger = Logger(name, logpath)
#        self.logger.log("%s starting!" % name)
        # skip_init will take things right to the ready state
        #  and mean no "initialize" transition is needed
        if skip_init:
            self.__state = "ready"
        else:
            self.__state = "stopped"
        self.__rpc_host = rpc_host
        self.__rpc_port = rpc_port
        self.run_params = None
        self.__dummy_val = 0
        self.contexts = [
            # ("sender", announcing_sender(self.name,
            #                              self.__rpc_host,
            #                              self.__rpc_port,
            #                              self.synchronous,
            #                              control_host=control_host)),
            ("rpc_server",
             rpc_server(port=self.__rpc_port,
                        funcs={"state": self.state,
                               "state_change": self.state_change})),
            ("runner", threadable(func=self.runner))]

    def state(self, name):
        if name != self.name:
            return "unknown"
        return self.__state

    def complete_state_change(self, name, requested):
        if name != self.name:
            return
        newstate = {"stopping": "ready",
                    "initializing": "ready",
                    "starting": "running",
                    "pausing": "paused",
                    "resuming": "running",
                    "terminating": "stopped",
                    "recovering": "stopped"}.get(requested, requested)
        trep = datetime.datetime.utcnow()
        self.__state = newstate
        # self.sender.send({"type": "moni",
        #                   "service": self.name,
        #                   "t": trep,
        #                   "varname": "state",
        #                   "value": newstate})

    def state_change(self, name, requested, state_args):
        if name != self.name:
            return
        trep = datetime.datetime.utcnow()
        # send this now before we call out for transition
        # self.sender.send({"type": "moni",
        #                   "service": self.name,
        #                   "t": trep,
        #                   "varname": "state",
        #                   "value": requested})
        # set out transition state now.
        self.__state = requested
        if requested == "starting":
            self.run_params = state_args
            self.start_running()
            # if self.synchronous:
            #     self.sender.send({"type": "moni",
            #                       "service": self.name,
            #                       "t": trep,
            #                       "varname": "rundata",
            #                       "value": assoc(self.run_params,
            #                                      "tstart", trep)})
        if requested == "stopping":
            self.stop_running()
        if requested == "pausing":
            self.pause_running()
        if requested == "initializing":
            self.run_params = state_args
            self.initialize()
        if requested == "resuming":
            self.resume_running()
        if requested == "terminating":
            self.terminate()
        if requested == "recovering":
            self.recover()

    def wakeup(self):
        self.runner.wakeup()

    def runner(self):
        """
        Component "ops" loop.  Called at threading hearbeat frequency,
        currently 1/sec.

        Overide this, and use it to check statuses, send periodic report,
        etc.

        """
        if self.__state == "running":
            self.__dummy_val += random.random() * 100 - 50
            # self.sender.send({"type": "moni",
            #                   "service": self.name,
            #                   "t": str(datetime.datetime.utcnow()),
            #                   "varname": "x",
            #                   "value": self.__dummy_val})

    def initialize(self):
        """
        Override this to explicitly do something during "initializing"
        transitional state (changing from "stopped" to "ready" states)

        Note: this is an optional transition.  You can call the default
        initialize in the constructor and go right to "ready"
        if that fits for your component.

        Be sure to report when your transition is complete.
        """
        self.complete_state_change(self.name, "initializing")

    def start_running(self):
        """
        Override this to explicitly do something during "starting" transitional
        state (changing from "ready" to "running" states)

        Be sure to report when your transition is complete.
        """
        self.complete_state_change(self.name, "starting")

    def stop_running(self):
        """
        Override this to explicitly do something during "stopping" transitional
        state (changing from "running" to "ready" states)

        Be sure to report when your transition is complete.
        """
        self.complete_state_change(self.name, "stopping")

    def pause_running(self):
        """
        Override this to explicitly do something during "pausing" transitional
        state (changing from "running" to "paused" states)

        Be sure to report when your transition is complete.
        """
        self.complete_state_change(self.name, "pausing")

    def resume_running(self):
        """
        Override this to explicitly do something during "resuming" transitional
        state (changing from "paused" to "running" states)

        Be sure to report when your transition is complete.
        """
        self.complete_state_change(self.name, "resuming")

    def terminate(self):
        """
        Override this to explicitly do something during "terminating"
        transitional state (changing from "ready" to "stopped" states)

        Be sure to report when your transition is complete.
        """
        self.complete_state_change(self.name, "terminating")

    def recover(self):
        """
        Override this to explicitly do something during
        "recovering" transitional state

        Perform resets, clean up file handles, etc.  Go back to
        a "clean stop" in the "stopped" state.

        Be sure to report when your transition is complete.
        """
        self.complete_state_change(self.name, "recovering")


def get_args():  # no-coverage
    parser = argparse.ArgumentParser(
        description="Simulated LBNE 35 ton component")
    parser.add_argument("-n", "--name", type=str, dest='name',
                        default="toy", help="Component name")
    parser.add_argument("-r", "--rpc-port", type=int, dest='rpc_port',
                        default=6660, help="RPC port")
    parser.add_argument("-H", "--rpc-host", type=str, dest='rpc_host',
                        default='localhost', help="This hostname/IP addr")
    parser.add_argument("-c", "--control-host", type=str, dest='control_host',
                        default='localhost', help="Control host")
    parser.add_argument("-s", "--is-synchronous", dest="synchronous",
                        default=False, action="store_true",
                        help="Component is synchronous (starts/stops w/ DAQ)")
    return parser.parse_args()


# def main():  # no-coverage
#     """
#     When not running `Component` under test, it can be instantiated on
#     the command line using `lbnecomp` (`lbnecomp -h` for help).
#     """
#     args = get_args()
#     with Component(logpath=os.path.join(os.environ["HOME"], ".lbnerc.log"),
#                    **vars(args)):
#         wait_for_interrupt()
