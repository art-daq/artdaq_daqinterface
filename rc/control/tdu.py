#! /usr/bin/env python

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from rc.tdu.tdu_control import tdu_control
from argparse import ArgumentParser
from rc.util import wait_for_interrupt
import os


class tdu:

    # Restrict to a particular path.
    class RequestHandler(SimpleXMLRPCRequestHandler):
        rpc_paths = ('/RPC2',)

    def __init__(self, logpath=None, process_name="tdu",
                 rc_host='localhost',
                 xml_host="localhost", xml_port=6659,
                 tdu_host='192.168.1.201', tdu_port=10001):

        self.name = process_name
        if logpath == '':
            logpath = os.path.join(os.environ["HOME"], ".tdu.log")

        # Create server
        server = SimpleXMLRPCServer((xml_host, xml_port),
                                    requestHandler=self.RequestHandler,
                                    logRequests=False)
        server.register_introspection_functions()

        # Register the tdu_control class methods
        server.register_instance(tdu_control(tdu_host, tdu_port,
                                             is_client=True,
                                             logpath=logpath))

        # Setup the XMLRPC server exit plan
        self.quit = False
        server.register_function(self.kill_xmlrpc_server)

        # Run the server's main loop
        while not self.quit:
            server.handle_request()

    def kill_xmlrpc_server(self):
        self.quit = True
        return 1


def main():  # no-coverage

    parser = ArgumentParser(description='Load an XMLRPC server'
                            ' to control the TDU')
    parser.add_argument('-n', '--process_name', default='tdu',
                        help='The name of the XMLRPC process in lbnerc. '
                        'Default: tdu')
    parser.add_argument('-c', '--rc_host', default='localhost',
                        help='The host on which lbnerc server runs. '
                        'Default: localhost')
    parser.add_argument('-H', '--xml_host', default='localhost',
                        help='The host on which the XMLRPC server runs. '
                        'Default: localhost')
    parser.add_argument('-r', '--xml_port', default=50008,
                        type=int,
                        help='The port on which the XMLRPC server runs. '
                        'Default: 50008')
    parser.add_argument('-T', '--tdu_host', default='192.168.1.201',
                        help='The host on the TDU to connect to. '
                        'Default: TDU master: 192.168.1.201')
    parser.add_argument('-P', '--tdu_port', default=10001,
                        type=int, help='The port on the TDU to connect to'
                        'Default 10001')
    args = parser.parse_args()

    tdu(logpath=os.path.join(os.environ["HOME"], ".tdu.log"), **vars(args))
