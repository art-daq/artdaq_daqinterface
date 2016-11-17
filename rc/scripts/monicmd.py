import argparse
import datetime
from rc.io import sender


def parse_args():
    parser = argparse.ArgumentParser(
        description="Send data into lbnecontrol")
    parser.add_argument("-t", "--datetime", type=str, dest='t',
                        default='',
                        help=("Time of monitored value, no whitespace (e.g. "
                              "2013-06-19_14:23:12.013253)"))
    parser.add_argument("-T", "--type", type=str, dest='valtype',
                        default='str', help="Value type (str, int, float)")
    parser.add_argument("-H", "--host", type=str, dest='host',
                        default="localhost",
                        help="Receiving hostname (default: localhost)")
    parser.add_argument("service")
    parser.add_argument("varname")
    parser.add_argument("value")

    return parser.parse_args()


def main():
    args = parse_args()
    if args.valtype == "int":
        value = int(args.value)
    elif args.valtype == "float":
        value = float(args.value)
    elif args.valtype == "str":
        value = args.value
    else:
        print ("Invalid data type '%s'. "
               "Only int, str or float values are allowed. "
               "Run with -h flag for help." % args.valtype)
        return

    if args.t:
        t = " ".join(args.t.split("_"))
    else:
        t = str(datetime.datetime.utcnow())
    with sender(ip=args.host, port=5000) as s:
        s.send({"type": "moni",
                "t": t,
                "service": args.service,
                "varname": args.varname,
                "value": value})
