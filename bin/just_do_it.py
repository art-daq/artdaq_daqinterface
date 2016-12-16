#!/bin/env python

import os
from time import sleep
import sys
sys.path.append( os.getcwd() )

import rc.control.daqinterface
from rc.control.daqinterface import DAQInterface

if len(sys.argv) != 2:
    print "Usage: " + os.path.basename( sys.argv[0] ) + " <run number>"
    sys.exit(1)

run_number = sys.argv[1]

with DAQInterface() as daqint:
    daqint.do_boot("docs/config_john.txt", {"component01":("mu2edaq01.fnal.gov", "5305")})
    sleep(10)
    daqint.do_config("demo")
    daqint.do_start_running(int(run_number))
    sleep(10)
    daqint.do_stop_running()
    daqint.do_terminate()
