import xmlrpclib
import socket
from argparse import ArgumentParser
from sys import exit

#parse the arguments
parser = ArgumentParser(description=
                        'Communicate with an XMLRPC server to control the TDU')
parser.add_argument('-T', '--xmlrpc_host',       default='localhost',
                    help='The host on the XMLRPC server to connect to. '
                    'Default: localhost')
parser.add_argument('-p', '--xmlrpc_port',       default=50008,    type=int,
                    help='The port on the XMLRPC server to connect to. '
                    'Default: 50008')
parser.add_argument('-k', '--kill_xmlrpc',       action='store_true',
                    help='Shutdown the XMLRPC server')
parser.add_argument('-P', '--do_ping',           action='store_true',
                    help='Do a ping '
                    '(note that the following commands can be all activated'
                    'at the same time, and run in the order shown here)')
parser.add_argument('-g', '--get_status',        action='store_true',
                    help='Get TDU status')
parser.add_argument('-s', '--do_time_sync',      action='store_true',
                    help='Do a time sync')
parser.add_argument('-d', '--do_delay_calc',     action='store_true',
                    help='Do a delay calculation (followed by a time sync)')
parser.add_argument('-t', '--test_all_commands', action='store_true',
                    help='Do a test (run all commands!)')

args = parser.parse_args()


s = xmlrpclib.ServerProxy('http://' + args.xmlrpc_host 
                          + ':' + str(args.xmlrpc_port))

if args.kill_xmlrpc:
    s.kill_xmlrpc_server()
    exit()

# Print list of available methods & exit if nothing else is required
if not (args.do_ping or args.do_time_sync or args.do_delay_calc 
        or args.test_all_commands or args.get_status):
    print parser.print_help()
    
    tempstr  = 'The following is a list of all available commands '
    tempstr += 'that can be used to control the TDU '
    tempstr += '(not all commands have been implemented in this script yet)'
    for c in s.system.listMethods():
        if 'system.' not in c:
            print c
    exit()

def print_result(result):
    try:
        len(result)
    except TypeError:
        #it's just an int
        test = result
    else:
        test = result[0]
    if test:
        text = "(FAILURE)"
    else:
        text = "(SUCCESS)"
    print result, text

try:
    if args.do_ping:
        print_result(s.do_ping())
    if args.get_status:
        print_result(s.get_status())
    if args.do_time_sync:
        print_result(s.do_time_sync())
    if args.do_delay_calc:
        print_result(s.do_delay_calc())
        print_result(s.do_time_sync())

    if args.test_all_commands:
        print_result('Testing all commands')
        print_result(s.debug_read_all_registers())
        print_result(s.do_delay_calc())
        print_result(s.do_ping())
        print_result(s.do_send_sync_pulse())
        print_result(s.do_time_sync())
        print_result(s.read_control_reg())
        print_result(s.read_error_registers())
        print_result(s.read_gps_status())
        print_result(s.read_tdu_id())
        print_result(s.read_tdu_status())

except xmlrpclib.Fault as e:
    print 'xmlrpclib.Fault caught:', e,
    print 'Attempting to kill TDU XMLPRC server...',
    try:
        s.kill_xmlrpc_server()
    except:
        print 'Failure'
    else:
        print 'Success'

except socket.error as e:
    print 'socket.error caught:', e, '   Is the XMLRPC server up?'
