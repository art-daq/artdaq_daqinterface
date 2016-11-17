import collections
import datetime
import json
import pprint
import logging
import logging.handlers


def make_dict(name, msg):
    return {"source": name,
            "t": str(datetime.datetime.utcnow()),
            "msg": msg}


class Logger(object):
    def __init__(self, source_name="log", file_name=None):
        self.file_name = file_name
        self.msgs = collections.deque(maxlen=1000)
        if self.file_name:
            mylogger = logging.getLogger("lbnelog")
            mylogger.setLevel(logging.DEBUG)
            handler = logging.handlers.RotatingFileHandler(
                self.file_name, maxBytes=100000000, backupCount=5)
            mylogger.addHandler(handler)
            self.log = lambda msg: mylogger.debug(json.dumps(
                make_dict(source_name, msg)))
        else:
            self.log = lambda msg: self.msgs.append(
                make_dict(source_name, msg))

    def __str__(self):  # no-coverage
        if self.file_name:
            return "Logger(%s)" % self.file_name
        else:
            return ("Logger:\n" +
                    pprint.PrettyPrinter().pformat(list(self.msgs)))
