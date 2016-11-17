import os
import math
import os.path
from rc.util import setup_django_env, wait_for_interrupt
from rc.log import Logger
setup_django_env()
from rc.web.control.models import Component, Moni, Runs
from rc.io import threaded_receiver
from rc.util import dict_datetime_from_str
from rc.util.contexts import ContextObject


class DBServ(ContextObject):
    def __init__(self, logpath=None):
        self.contexts = [
            ("queue", "recv_thread",
             threaded_receiver(rargs={"port": 7000},
                               func=self.__handle_message))]
        self.__logger = Logger("dbserv", logpath)
        self.__logger.log("DBServ started")

    def __handle_message(self, m):
        self.__logger.log(m)
        cmd = m.get("cmd", None)
        if cmd == "complist":
            for compjson in m.get("comps", []):
                Component.objects.get_or_create(name=compjson["name"])
        elif cmd == "moni":
            moni = dict_datetime_from_str(m["payload"])
            value = moni["value"]
            if type(value) in (float, int):
                if (math.isnan(value) == False) and moni["t"] is not None:
                    m = Moni(service=moni["service"],
                             varname=moni["varname"],
                             value=value,
                             t=moni["t"])
                    m.save()
                else:
                    self.__logger.log("Got a NAN: %s:%s" % (moni["service"],
                                                            moni["varname"]))
            if moni["varname"] == "state":
                try:
                    comp = Component.objects.get(name=moni["service"])
                    comp.state = moni["value"]
                    comp.save()
                except Component.DoesNotExist:
                    self.__logger.log("State update for unknown component")
        elif cmd == "rstart":
                #print "Got start dump: ", m["payload"]
                sinfo = m["payload"]
                r = Runs(run = sinfo["runnum"], config = sinfo["config"],
                         runtype = sinfo["runtype"], components = sinfo["complist"],
                         start = sinfo["starttime"])
                r.save()
        elif cmd == "rstop":
                #print "Got stop dump: ", m["payload"]
                sinfo = m["payload"]
                try:
                    r = Runs.objects.get(run=sinfo["runnum"])
                    r.stop = sinfo["stoptime"]
                    r.save()
                except Runs.DoesNotExist:
                    self.__logger.log("Run update for unknown run")


def main():  # no-coverage
    with DBServ(logpath=os.path.join(os.environ["HOME"], ".lbnerc.log")):
        wait_for_interrupt()
