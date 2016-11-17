import argparse
from datetime import datetime
import pytz
from re import search
import time
import os
import random
import csv
import shutil
import hashlib
import random
import string
import urllib2
from rc.log import Logger
from rc.io import sender
from rc.io.rpc import rpc_server
from rc.threading import threadable
from rc.util.contexts import ContextObject
from rc.util import wait_for_interrupt
from rc.control.component import Component, announcing_sender
from rc.control.hvcryo_dict import slow_control_id_dict as ids

class HVCryoReporter(Component):
    """
    This program parses Alan's 35T slow control monitoring output
    and reports to both rc/control and the CondDB
    """
    __MAXPORT = 65535

    def __init__(self, logpath=None, name="hvcryo",
                 rpc_host="localhost", control_host='localhost',
                 synchronous=False, rpc_port=6660,
                 input_dir='./data'):

        # Call your base class __init__ function
        Component.__init__(self, logpath=logpath,
                           name=name,
                           rpc_host=rpc_host,
                           control_host=control_host,
                           synchronous=False,
                           rpc_port=rpc_port,
                           skip_init=True)
        # go right to the ready state
        #self.complete_state_change(self.name, "initializing")
        self.input_dir = input_dir
        self.logger.log("HVCryo Init Done.")
        self.logger.log("Input directory is %s" % self.input_dir)
        #print "known id pairs: ", ids

    def runner(self):
        """
        Component "ops" loop.  Called at threading hearbeat frequency,
        currently 1/sec.
        """
        if self.state(self.name) == "running":
            # look for, parse and load files.
            file_list = os.listdir(self.input_dir)
            #if len(file_list) != 0:
            #    print "Found files, number of files:",len(file_list)
            ## Avoid a race condition with the file writer.  Wait a bit.
            time.sleep(2)
            for afile in file_list:
                current_file = os.path.join(self.input_dir, afile)
                if afile.endswith('.csv'):
                    print current_file
                    slc_csv =[]
                    slc_csv.append("channel, tv, rvalue\n")
                    with open(current_file) as f:
                        #junk = f.next()  # skip the "[Data]" line
                        reader = csv.reader(f)
                        for row in reader:
                            # csv file:  [name, date, value]
                            # save the fractional seconds...
                            temptime = row[1].split('.')
                            nowtime = datetime.strptime(temptime[0],
                                                        '%m/%d/%Y %H:%M:%S')
                            # reported times expect the usec precision, use the tempfracsec
                            if len(temptime)>1:
                                tempfracsec = temptime[1]
                            else:
                                tempfracsec = '0'
                            tempfracsec = tempfracsec[:6]  # truncate to microseconds
                            tempfracsec += (6 - len(tempfracsec)) * '0'  # add 0s
                            #nowtime2 = nowtime.replace(microsecond=int(tempfracsec),
                            #                           tzinfo=pytz.timezone('America/Chicago'))
                            nowtime2 = nowtime.replace(microsecond=int(tempfracsec))
                            chi_tz = pytz.timezone('America/Chicago')
                            nowtime2_tz = chi_tz.localize(nowtime2, is_dst=True)
                            # convert to UTC, and remove tzinfo
                            nowtime3 = nowtime2_tz.astimezone(pytz.utc)
                            nowtime4 = nowtime3.replace(tzinfo=None)
                            tag = row[0]
                            # remove the .F_CV
                            tag = tag[:-5].upper()
                            value = float(row[2])
                            #print nowtime4, tag, value
                            self.sender.send({"type": "moni",
                                    "service": self.name,
                                    "t": str(nowtime4),
                                    "varname": tag,
                                    "value": float(value)})

                            if tag in ids:
                                id_idx = ids[tag]
                                uni_time = time.mktime(nowtime4.timetuple())
                                slc_csv.append("%d, %f, %f\n" % (id_idx, uni_time, float(value)))
                            else:
                                print "Unknown ID found in input file: ", tag
                    os.remove(current_file)
                    #report the file to ConDb
                    self.send_report_condb(slc_csv)

    def start_running(self):
        self.logger.log("Starting HVCRYO reporter")
        self.complete_state_change(self.name, "starting")


    def send_report_condb(self, csv_in = []):
        #print csv_in
        random.seed()   # initialize from time
        # generate random salt
        salt = ''.join(random.choice(string.ascii_letters+string.digits) for x in range(100))
        password = 'Saz54y'

        m = hashlib.md5()
        m.update(password)
        m.update(salt)
        m.update("table=dune35t.daq_slowcontrols")
        for line in csv_in:  m.update(line)
        signature = m.hexdigest()

        request = urllib2.Request("http://dbdata0vm.fnal.gov:8117/LBNE35tCon/app/put?table=dune35t.daq_slowcontrols",
                                  "".join(csv_in),
                {  "X-Salt": salt,
                    "X-Signature": signature })
        response = urllib2.urlopen(request)
        print response.read()


def get_args():  # no-coverage
    parser = argparse.ArgumentParser(
        description="HVCRYO reporter- A 35 ton component")
    parser.add_argument("-n", "--name", type=str, dest='name',
                        default="hvcryo", help="Component name")
    parser.add_argument("-r", "--rpc-port", type=int, dest='rpc_port',
                        default=6660, help="RPC port")
    parser.add_argument("-H", "--rpc-host", type=str, dest='rpc_host',
                        default='localhost', help="This hostname/IP addr")
    parser.add_argument("-c", "--control-host", type=str, dest='control_host',
                        default='localhost', help="Control host")
    parser.add_argument("-d", "--input-dir", type=str, dest='input_dir',
                        default='./data', help="Input csv file directory")
    return parser.parse_args()


def main():  # no-coverage
    """
    When not running `Component` under test, it can be instantiated on
    the command line using `lbnecomp` (`lbnecomp -h` for help).
    """
    args = get_args()
    with HVCryoReporter(logpath=os.path.join(os.environ["HOME"], ".lbnerc.log"),
                      **vars(args)):
        wait_for_interrupt()
