import os
import sys
sys.path.append( os.environ["DAQINTERFACE_BASEDIR"] )

import zmq
from rc.InhibitMaster import InhibitMaster
import os, sys, time

sys.path.append( os.getcwd() )

def do_enable_base(self):
    context = zmq.Context()
    publisher = InhibitMaster.StatusPUBNode(context,"tcp://*:5556")
    time.sleep(0.5)
    publisher.send_status_msg("DAQINTERFACE","ENABLE","OK")


def do_disable_base(self):
    context = zmq.Context()
    publisher = InhibitMaster.StatusPUBNode(context,"tcp://*:5556")
    time.sleep(0.5)
    publisher.send_status_msg("DAQINTERFACE","ENABLE","ERROR")


