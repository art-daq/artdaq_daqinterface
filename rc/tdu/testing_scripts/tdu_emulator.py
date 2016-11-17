from rc.tdu.tdu_control import tdu_control
from argparse import ArgumentParser


#parse the arguments
parser = ArgumentParser(description=
                        'Initialise a TDU emulator. Testing purposes only')
parser.add_argument('-T', '--tduem_host', default='',
                    help=
                    "The host on which to run the TDU emulator. Default: ''")
parser.add_argument('-P', '--tduem_port', default=50007, type=int, 
                    help='The port on which to run the TDU emulator')
args = parser.parse_args()


#CONSTRUCTOR FOR CREATING EMULATOR
tdu = tdu_control(HOST=args.tduem_host, PORT=args.tduem_port, is_client=False)

#emulator emulates only 2 registers:
##control - this is writeable by the user. Defaults to 0x0000
##status  - sets it to 0x0008 (ready to sync) or 0x8000 (not ready)
##          set by looking at the control register
###         0x0000        -> 0x0008
###         anything else -> 0x8000
#emulator is persistent (many connections allowed to come & go)
#exit with Ctrl-C

