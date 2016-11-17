from rc.io import sender
import atexit
import optparse
import os
import readline
import json


def get_options():
    prs = optparse.OptionParser()
    prs.add_option("-H", "--moni-host", dest="monihost", default="localhost",
                   help="Host to send to (default: localhost)")
    return prs.parse_args()[0]


def main():
    opt = get_options()
    histfile = os.path.join(os.path.expanduser("~"), ".lbnerepl_history")
    try:
        readline.read_history_file(histfile)
    except IOError:
        # Pass here as there isn't any history file, so one will be
        # written by atexit
        pass
    atexit.register(readline.write_history_file, histfile)
    with sender(ip=opt.monihost) as client:
        while True:
            try:
                txt = raw_input('moni>  ')
                if not txt.strip():
                    continue
                parsed = json.loads(txt)
            except (EOFError, KeyboardInterrupt):
                print
                break
            except json.decoder.JSONDecodeError:
                print '"%s" is not valid JSON.' % txt
            else:
                if type(parsed) is dict:
                    client.send(parsed)
                else:
                    print "Must enter a dictionary/hash table to send!"
