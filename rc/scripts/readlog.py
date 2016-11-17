import sys
import json


def read_from_input():
    while True:
        l = sys.stdin.readline()
        if not l:
            return
        d = json.loads(l)
        print "%s[%s]: %s" % (d["source"],
                              d["t"],
                              d["msg"])


def main():
    try:
        read_from_input()
    except KeyboardInterrupt:
        return
