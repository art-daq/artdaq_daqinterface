from rc.tdu.tdu_control import tdu_control
from argparse import ArgumentParser


#parse the arguments
parser = ArgumentParser(description='Load a tdu_control to control the TDU. '
                        'Testing purposes only')
parser.add_argument('-T', '--tdu_host',      default='192.168.1.201',
                    help='The host on the TDU to connect to. '
                    'Default: TDU master: 192.168.1.201')
parser.add_argument('-P', '--tdu_port',      default=10001, type=int,
                    help='The port on the TDU to connect to. Default: 10001')
parser.add_argument('-t', '--do_test',       action='store_true',
                    help='Do a test (read all registers!)')
parser.add_argument('-d', '--do_delay_calc', action='store_true',
                    help='Do a delay calculation')
args = parser.parse_args()


#CONSTRUCTOR FOR TESTING WITH EMULATOR ON OXFORD MACHINE
#tdu = tdu_control(HOST='pplxint8.physics.ox.ac.uk', PORT=50007, is_client=True)

#CONSTRUCTOR FOR TESTING WITH REAL TDU ON LBNEDAQ
#tdu = tdu_control(HOST='192.168.1.201', PORT=10001, is_client=True)

tdu = tdu_control(HOST=args.tdu_host, PORT=args.tdu_port, is_client=True)


if not tdu.do_ping():
    if args.do_test:
        tdu.debug_read_all_registers()
    if args.do_delay_calc:
        tdu.do_delay_calc()
    tdu.do_time_sync()

tdu.close_socket()
