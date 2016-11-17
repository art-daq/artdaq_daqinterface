import argparse
import datetime
import os.path
import os
import random
import serial
from toolz import assoc
from contextlib import contextmanager
from rc.log import Logger
from rc.io import sender
from rc.io.rpc import rpc_server
from rc.threading import threadable
from rc.util.contexts import ContextObject
from rc.util import wait_for_interrupt
from rc.control.component import Component, announcing_sender


class Temps(Component):
    """
    Temp logger example
    """
    __MAXPORT = 65535

    def __init__(self, logpath=None, name="toycomponent",
                 rpc_host="localhost", control_host='localhost',
                 synchronous=False, rpc_port=6659):
        print "Welcome to Temps.__init__"
        Component.__init__(self, logpath=logpath,
                           name=name,
                           rpc_host=rpc_host,
                           control_host=control_host,
                           synchronous=synchronous,
                           rpc_port=rpc_port)

        self.port_name = '/dev/ttyACM0'
        self.baud_rate = 9600
        print "Done init"

    def runner(self):
        if self.state(self.name) == "running":
            line = ""
            while len(line) < 1:
                line = self.__sp.readline().strip('\n\r')
            temp = float(line)
            print "Found temp: ", temp, " type: ", type(temp)
            self.logger.log("Temp %f" % temp)
            self.sender.send({"type": "moni",
                              "service": self.name,
                              "t": str(datetime.datetime.utcnow()),
                              "varname": "PSC_2208E_Temp",
                              "value": temp})

    def start_running(self):
        self.logger.log("Open serial line")
        self.__sp = serial.Serial()
        self.__sp.port = self.port_name
        self.__sp.baudrate = self.baud_rate
        self.__sp.open()
        # Get rid of any junk..
        trash = self.__sp.readline()
        self.logger.log("Serial port online")
        self.complete_state_change(self.name, "starting")

    def stop_running(self):
        self.logger.log("Closing down serial")
        self.__sp.close()
        self.complete_state_change(self.name, "stopping")


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


def main():  # no-coverage
    """
    When not running `Component` under test, it can be instantiated on
    the command line using `lbnecomp` (`lbnecomp -h` for help).
    """
    args = get_args()
    with Temps(logpath=os.path.join(os.environ["HOME"], ".lbnerc.log"),
               **vars(args)):
        wait_for_interrupt()
