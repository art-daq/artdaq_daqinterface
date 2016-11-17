from __future__ import print_function
from contextlib import contextmanager
from rc.io import queueing_receiver, sender, pubsender
from rc.io.rpc import rpc_server, rpc_client
from rc.log import Logger
from rc.threading import threadable
from rc.util.contexts import ContextObject, apply_on_exception
from rc.util import wait_for_interrupt, wait_until, dict_datetime_from_str
from rc.util import stringify_times
from rc.util.exc_string import exc_string
from rc.compatibility import Queue
from safelist import SafeList
from toolz import assoc
from re import search
import collections
import os
import os.path
import socket
import argparse
import datetime
import xmlrpclib
import psycopg2


class DAQComponentListMgr(object):
    daqCompListFile = os.path.join(os.environ["HOME"], ".lbnerc-components")

    @classmethod
    def getDaqComponentsFromFile(cls):
        daqcomplist = {}
        if not os.path.exists(cls.daqCompListFile):
            # Testing list.
            daqcomplist["RCE01"] = ("lbnedaq01", "3344")
            daqcomplist["RCE02"] = ("lbnedaq02", "3345")
            return daqcomplist
        with open(cls.daqCompListFile) as f:
            rawcomplist = f.read().splitlines()
            for rawcomp in rawcomplist:
                comptup = rawcomp.split(" ")
                compkey = comptup[0].replace(":", "")
                daqcomplist[compkey] = (comptup[1],
                                        comptup[2])
            return daqcomplist


class RunNumberPersistence(object):
    runNumberFile = os.path.join(os.environ["HOME"], ".lbnerc-run")

    @classmethod
    def getRunFromFile(cls):
        if not os.path.exists(cls.runNumberFile):
            return 0
        with open(cls.runNumberFile) as f:
            line = f.readline()
            m = search('(\d+)', line)
            if not m:
                return 0
            return int(m.group(1))

    @classmethod
    def saveRunSubrunToFile(cls, run):
        with open(cls.runNumberFile, "w") as f:
            f.write("%d" % (run))


class DAQPersistenceLayer(object):
    """
    Store a bunch of DAQ specific stuff for use during ops, including:
    * Previous run number.  Increment and assign at start
    * Operator selected configuration
    * Available components that are DAQ configurable
    * User selected list of components
    """
    def __init__(self):
        self.__prev_run_number = RunNumberPersistence.getRunFromFile()
        self.__config = "No Config"
        self.__available_daqcomps = \
            DAQComponentListMgr.getDaqComponentsFromFile()
        # Default comps list:  the full set.
        self.__selected_daqcomps = self.__available_daqcomps
        self.__run_type = "Test"
        self.__allowed_run_types = ["Test",
                                    "Physics",
                                    "Commissioning",
                                    "Calibration"]

    def newrun(self):
        self.__prev_run_number += 1
        RunNumberPersistence.saveRunSubrunToFile(self.__prev_run_number)
        return self.run_params()

    def setconfig(self, config):
        self.__config = config
        return None

    def setruntype(self, runtype):
        if runtype.capitalize() not in self.__allowed_run_types:
            raise ValueError("Requested Run Type (%s) not in "
                             "allowed list (%s)" %
                             (runtype, str(self.__allowed_run_types)))
        self.__run_type = runtype.capitalize()
        return True

    def setdaqcomps(self, selected_daqcomps):
        new_daqcomps = {}
        for dcomp in selected_daqcomps:
            if dcomp not in self.__available_daqcomps:
                raise ValueError("Requested DAQcomponent (%s) not in list"
                                 " of available DAQcomponents." % dcomp)
            new_daqcomps[dcomp] = self.__available_daqcomps[dcomp]
        self.__selected_daqcomps = new_daqcomps
        return True

    def adddaqcomps(self, added_daqcomps):
        new_daqcomps = self.__selected_daqcomps
        for dcomp in added_daqcomps:
            if dcomp not in self.__available_daqcomps:
                raise ValueError("Requested DAQcomponent (%s) not in list"
                                 " of available DAQcomponents." % dcomp)
             #silently ignore any add requests already present
            if dcomp not in new_daqcomps:
                new_daqcomps[dcomp] = self.__available_daqcomps[dcomp]
        self.__selected_daqcomps = new_daqcomps
        return True

    def rmdaqcomps(self, rmd_daqcomps):
        new_daqcomps = {}
        for dcomp in rmd_daqcomps:
            if dcomp not in self.__selected_daqcomps:
                raise ValueError("Requested DAQcomponent (%s) to be removed"
                                 " not in selected DAQcomponents." % dcomp)
        for dcomp in self.__selected_daqcomps:
            if dcomp not in rmd_daqcomps:
                new_daqcomps[dcomp] = self.__available_daqcomps[dcomp]
        self.__selected_daqcomps = new_daqcomps
        return True

    def getdaqcomplists(self):
        ret = []
        ret.append("Available:")
        for name in sorted(self.__available_daqcomps):
            ostring = (name + " (" +
                       self.__available_daqcomps[name][0] +
                       ":" + self.__available_daqcomps[name][1] +
                       ")")
            ret.append(ostring)
        ret.append("")
        ret.append("Selected:")
        for name in sorted(self.__selected_daqcomps):
            ostring = (name + " (" +
                       self.__selected_daqcomps[name][0] +
                       ":" + self.__selected_daqcomps[name][1] +
                       ")")
            ret.append(ostring)
        return ret

    def run_params(self):
        return {"run_number": self.__prev_run_number,
                "config": self.__config,
                "run_type": self.__run_type,
                "daq_comp_list": self.__selected_daqcomps}


class ConfigListLayer(object):
    """
    Manage the connection to the configuration manager
    listing service.  Hide all the ugly here...

    Returns:  None if no DB connection specified, or a list of configs
    """
    def __init__(self):
        self.__lbnedb_conn = xmlrpclib.ServerProxy(
            "http://localhost:8080/RPC2")

    def get_config_list(self):
        try:
            db_list = self.__lbnedb_conn.cfgs.getList(0, 0)
            config_list = []
            for config in db_list.keys():
                # times need to be strings for xmlrpc layer
                config_list.append({"config_label": config,
                                    "config_desc": db_list[config]})
        except socket.error as v:
            # You get a dummy entry, useful for testing
            print("Error connecting to CfgMgr: %s" % v)
            config_list = []
            config_list.append({"config_label": "dummy",
                                "config_desc": "Dummy description"})

        return config_list

    def check_config(self, config_name):
        known_configs = self.get_config_list()
        ret = False
        for config in known_configs:
            if str(config["config_label"]) == config_name:
                ret = True
        return ret

    def check_server(self):
        # Ensure that the CfgMgr server is one
        try:
            db_check = self.__lbnedb_conn.system.listMethods()
            return True
        except socket.error as v:
            return False


class DBInterfaceLayer(object):
    """
    Manage the connection to the the Postgres DB and configuration
    listing tables.  Hide all the postgres ugly here...
    """
    def __init__(self, lbnedb_host=None):
        if lbnedb_host is not None:
            self.__lbnedb_conn = psycopg2.connect(
                "dbname=lbne35t_prod user=lbnedaq host=%s" % lbnedb_host)
        else:
            self.__lbnedb_conn = None

    def insert_start(self, run_number, config_name, run_type,
                     comp_list, start_time):
        if self.__lbnedb_conn is not None:
            db_cur = self.__lbnedb_conn.cursor()
            db_cur.execute("insert into dune35t.run_summary "
                           "(run,configuration_label,run_type,"
                           "component_list,start) "
                           "values (%s,%s,%s,%s,%s)",
                           (run_number, config_name, run_type,
                            comp_list, start_time)
                           )
            self.__lbnedb_conn.commit()
            db_cur.close()
            return success()
        else:
            return("No connection to DB available")

    def update_stop(self, run_number, stop_time):
        if self.__lbnedb_conn is not None:
            db_cur = self.__lbnedb_conn.cursor()
            db_cur.execute("update dune35t.run_summary "
                           "set stop=%s where "
                           "run=%s",
                           (stop_time, run_number)
                           )
            self.__lbnedb_conn.commit()
            db_cur.close()
            return success()
        else:
            return("No connection to DB available")


def success(dikt={}):
    return assoc(dikt, "succeeded", True)


def fail(reason):
    return {"succeeded": False, "reason": reason}


class Control(ContextObject):
    """
    Main Run Control object. Handles the following functions:

    1. Accept user commands via XML-RPC
    2. Listen for new components announcing themselves via ZeroMQ
    3. Controls (starts/stops) components via XML-RPC
    4. Listens for component state changes and other monitoring
       variables, via ZeroMQ.
    5. Reports events and monitored variables to Web server database
       process, `lbnedbserv`.

    """
    def __init__(self, logpath=None, web_host='localhost',
                 poll_period=0.01, lbnedb_host=None):
        self.__comps = SafeList()
        self.__poll_period = poll_period
        self.__logger = Logger("control", logpath)
        self.__logger.log("control object initialized")
        self.__latest_msgs = collections.deque(maxlen=1000)
        self.__recent_moni = collections.deque(maxlen=1000)
        self.__num_msgs_recvd = 0  # Includes msgs dropped from deque
        self.__dp_layer = DAQPersistenceLayer()
        self.__config_layer = ConfigListLayer()
        # manage and save a connection to postgres DB
        self.__logger.log("db is %s" % lbnedb_host)
        self.__db_layer = DBInterfaceLayer(lbnedb_host=lbnedb_host)
        self.contexts = [("exception_logger",
                          apply_on_exception(self.__print_logger)),
                         ("rpc_server",
                          rpc_server(funcs={"check": self.check,
                                            "start": self.start,
                                            "ignore": self.ignore,
                                            "control": self.control,
                                            "pause": self.pause,
                                            "resume": self.resume,
                                            "listruntype": self.listruntype,
                                            "setruntype": self.setruntype,
                                            "listconfigs": self.listconfigs,
                                            "setconfig": self.setconfig,
                                            "listdaqcomps": self.listdaqcomps,
                                            "setdaqcomps": self.setdaqcomps,
                                            "adddaqcomps": self.adddaqcomps,
                                            "rmdaqcomps": self.rmdaqcomps,
                                            "getsettings": self.getsettings,
                                            "initialize": self.initialize,
                                            "terminate": self.terminate,
                                            "stop": self.stop})),
                         ("queue", "recv_thread", queueing_receiver()),
                         ("msghdlr_thread",
                          threadable(func=self.__message_handler,
                                     period=self.__poll_period)),
                         ("web_sender", sender(ip=web_host,port=7000)),
                         ("pub_sender", pubsender(port=8000))
                         ]

    def __print_logger(self):  # no-coverage
        print(self.__logger)

    def __changestate(self, base_states, next_state, compnames=[]):
        def get_target_comps(compnames):
            if compnames == ["daq"]:
                return self.__comps.find(lambda c: c["synchronous"])
            elif "daq" in compnames:
                raise ValueError("Cannot change DAQ state alongside "
                                 "asynchronous components!")
            else:
                ret = [self.__get_component(cn) for cn in compnames]
                if True in [c["synchronous"] for c in ret]:
                    raise ValueError("%s cannot change state on its own; "
                                     "use 'daq' instead." % c["name"])
                return ret

        try:
            comps = get_target_comps(compnames)
        except ValueError as ve:
            return fail(str(ve))

        comps_not_ready = [
            c["name"]
            for c in comps
            if self.component_state(c["name"]) not in base_states]
        # Make sure they are all ready:
        if comps_not_ready:
            return fail(', '.join(comps_not_ready)
                        + " not in one of %s!" % base_states)

        # actual state change:
        is_stopping = False
        is_starting = False
        for comp in comps:
            with self.__component_connection(comp["name"]) as conn:
                if comp["synchronous"]:
                    if next_state == "starting":
                        state_args = self.__dp_layer.newrun()
                        is_starting = True
                    elif next_state == "initializing":
                        state_args = self.__dp_layer.run_params()
                    elif next_state == "stopping":
                        state_args = {}
                        is_stopping = True
                    else:
                        state_args = {}
                else:
                    state_args = {}
                conn.state_change(comp["name"], next_state, state_args)
        if is_starting:
            # make sure the DB knows about this
            time_now = str(datetime.datetime.utcnow())
            self.__logger.log("DB_start run %s" %
                              self.__dp_layer.run_params()["run_number"])
            self.__logger.log("DB_start config %s" %
                              self.__dp_layer.run_params()["config"])
            self.__logger.log("DB_start time %s" % time_now)
            daq_comp_string = ",".join(self.__dp_layer.
                                       run_params()["daq_comp_list"].keys())
            self.__logger.log("DB_start comps %s" % daq_comp_string)
            self.__db_layer.insert_start(run_number=self.__dp_layer.
                                         run_params()["run_number"],
                                         config_name=self.__dp_layer.
                                         run_params()["config"],
                                         run_type=self.__dp_layer.
                                         run_params()["run_type"],
                                         comp_list=daq_comp_string,
                                         start_time=time_now)
            rstart_info = {"runnum": self.__dp_layer.run_params()["run_number"],
                           "config": self.__dp_layer.run_params()["config"],
                           "runtype": self.__dp_layer.run_params()["run_type"],
                           "starttime": time_now,
                            "complist": daq_comp_string
                            }
            self.web_sender.send({"cmd": "rstart",
                                  "payload": rstart_info
                                  })

        if is_stopping:
            # make sure the DB get an update
            time_now = str(datetime.datetime.utcnow())
            self.__logger.log("DB_stop run %s" %
                              self.__dp_layer.run_params()["run_number"])
            self.__logger.log("DB_stop time %s" % time_now)
            self.__db_layer.update_stop(run_number=self.__dp_layer.
                                        run_params()["run_number"],
                                        stop_time=time_now)
            rstop_info = {"runnum": self.__dp_layer.run_params()["run_number"],
                          "stoptime": time_now
                          }
            self.web_sender.send({"cmd": "rstop",
                                  "payload": rstop_info
                                  })
        return success()

    def ignore(self, compnames=[]):
        for cname in compnames:
            if not self.__comps.find(lambda c: c["name"] == cname):
                return fail("not_found")
        self.__comps.remove(lambda c: c["name"] in compnames)
        return success()

    def control(self, args):
        badargs = ("'control' expects name, hostname, port "
                   "and 'synchronous' or 'asynchronous'")
        try:
            name, host, port, synctype = args
        except ValueError:
            return fail(badargs)
        if synctype not in ["synchronous", "asynchronous"]:
            return fail(badargs)
        if self.__comps.find(lambda c: c["name"] == name):
            return fail("Component '%s' is already being controlled!" % name)
        # Test actual existence of component, and verify that it's stopped:
        with rpc_client(host=host, port=port,
                        timeout=self.__poll_period) as c:
            state = c.state(name)
            if state == "unknown":
                return fail("Component %s doesn't answer or is unknown." %
                            name)
            if state not in ["stopped", "paused"]:
                return fail("Component %s is not in the stopped or "
                            "paused state!" % name)
        synchronous = True if synctype == "synchronous" else False
        self.__update_components_list(name, host, port, synchronous)
        return success()

    def pause(self, compnames=[]):
        return self.__changestate(["running"], "pausing", compnames=compnames)

    def resume(self, compnames=[]):
        return self.__changestate(["paused"], "resuming", compnames=compnames)

    def start(self, compnames=[]):
        return self.__changestate(["ready"], "starting",
                                  compnames=compnames)

    def stop(self, compnames=[]):
        return self.__changestate(["running", "paused"], "stopping",
                                  compnames=compnames)

    def initialize(self, compnames=[]):
        return self.__changestate(["stopped"], "initializing",
                                  compnames=compnames)

    def terminate(self, compnames=[]):
        return self.__changestate(["ready"], "terminating",
                                  compnames=compnames)

    def check(self, comps=None):
        if comps:
            try:
                compdicts = [self.__get_component(cname) for cname in comps]
                return success(
                    {"components": [assoc(c, "state",
                                          self.component_state(c["name"]))
                                    for c in compdicts]})
            except ValueError, v:
                return fail(str(v))

        comps_w_state = [assoc(c, "state",
                               self.component_state(c["name"]))
                         for c in self.__comps.list()]

        check_cfgmgr = self.__config_layer.check_server()

        all_running = (set(c["state"] for c in comps_w_state) ==
                       set(["running"]))

        rdict = success({"components": comps_w_state,
                         "cfgmgrok": check_cfgmgr})

        if all_running:
            parms = self.__dp_layer.run_params()
            return assoc(rdict, "run_params", parms)
        else:
            return rdict

    def listconfigs(self, comps=None):
        return (self.__config_layer.get_config_list(),
                self.__dp_layer.run_params()["config"])

    def listruntype(self, comps=None):
        return (self.__dp_layer.run_params()["run_type"])

    def setconfig(self, args):
        daq_comps = self.__comps.find(lambda c: c["synchronous"])
        for comp in daq_comps:
            if self.component_state(comp["name"]) not in ["stopped"]:
                return fail("daq not in the stopped state")
        print("Checking config:", args[0])
        if self.__config_layer.check_config(args[0]):
            self.__dp_layer.setconfig(args[0])
            return success()
        else:
            failstring = "Config not found in CfgMgr: {0:s}".format(args[0])
            return fail(failstring)

    def setruntype(self, args):
        daq_comps = self.__comps.find(lambda c: c["synchronous"])
        for comp in daq_comps:
            if self.component_state(comp["name"]) not in ["stopped"]:
                return fail("daq not in the stopped state")
        if len(args) == 0:
            return fail("Please specify a Runtype")
        try:
            self.__dp_layer.setruntype(args[0])
        except ValueError as ve:
            return fail(str(ve))
        return success()

    def listdaqcomps(self, comps=None):
        mylist = self.__dp_layer.getdaqcomplists()
        return mylist

    def setdaqcomps(self, args):
        daq_comps = self.__comps.find(lambda c: c["synchronous"])
        for comp in daq_comps:
            if self.component_state(comp["name"]) not in ["stopped"]:
                return fail("daq not in the stopped state")
        try:
            self.__dp_layer.setdaqcomps(args)
        except ValueError as ve:
            return fail(str(ve))
        return success()

    def adddaqcomps(self, args):
        daq_comps = self.__comps.find(lambda c: c["synchronous"])
        for comp in daq_comps:
            if self.component_state(comp["name"]) not in ["stopped"]:
                return fail("daq not in the stopped state")
        try:
            self.__dp_layer.adddaqcomps(args)
        except ValueError as ve:
            return fail(str(ve))
        return success()

    def rmdaqcomps(self, args):
        daq_comps = self.__comps.find(lambda c: c["synchronous"])
        for comp in daq_comps:
            if self.component_state(comp["name"]) not in ["stopped"]:
                return fail("daq not in the stopped state")
        try:
            self.__dp_layer.rmdaqcomps(args)
        except ValueError as ve:
            return fail(str(ve))
        return success()


    def getsettings(self, comps=None):
        rdict = success()
        parms = self.__dp_layer.run_params()
        return assoc(rdict, "run_params", parms)

    def components(self):
        return self.__comps.list()

    def __get_component(self, name):
        try:
            return self.__comps.find(lambda c: c["name"] == name)[0]
        except IndexError:
            raise ValueError("Component %s is unknown!" % name)

    @contextmanager
    def __component_connection(self, name):
        component = self.__get_component(name)
        with rpc_client(host=component["host"],
                        port=component["port"],
                        timeout=self.__poll_period) as c:
            yield c

    def component_state(self, name):
        if not self.__comps.find(lambda c: c["name"] == name):  # no-coverage
            return "unknown"
        try:
            with self.__component_connection(name) as c:
                return c.state(name)
        except socket.error:
            return "missing"

    def change_component_state(self, name, newstate):
        if self.__get_component(name)["synchronous"]:
            raise ValueError("Can't change state for synchronous components "
                             "individually; use 'daq' instead.")

        if newstate not in ["starting", "stopping", "recovering", "pausing",
                            "initializing", "resuming", "terminating"]:
            raise ValueError("State %s is not an allowed transition state!"
                             % newstate)
        with self.__component_connection(name) as c:
            c.state_change(name, newstate, {})
        return success()

    def __update_components_list(self, name, host, port, synchronous):
        comp = {"name": name,
                "host": host,
                "port": port,
                "synchronous": synchronous}
        self.__comps.add_or_update(lambda m: m["name"] == name, comp)
        self.web_sender.send({"cmd": "complist",
                              "comps": self.__comps.list()})

    def __handle_message(self, m):
        self.__latest_msgs.append(dict_datetime_from_str(m))
        self.__num_msgs_recvd += 1
        self.__logger.log("%s" % m)
        if m.get("type", "unknown") == "control":
            self.__update_components_list(m["name"],
                                          m["host"],
                                          m["port"],
                                          m["synchronous"])
            self.__logger.log("Controlling component %s at %s:%d" %
                              (m["name"], m["host"], m["port"]))
        elif m.get("type", "unknown") == "moni":
            if (m["service"] == "RCReporter") and (m["varname"][:4] == "RCE."):
               pass
            else:
                self.web_sender.send({"cmd": "moni",
                                      "payload": m})
            self.pub_sender.send({"cmd": "moni",
                                  "payload": m})
            self.__recent_moni.append(dict_datetime_from_str(m))

    def __message_handler(self):
        self.recv_thread.wakeup()
        while True:
            try:
                m = self.queue.get(timeout=self.__poll_period)
                self.__handle_message(m)
            except Queue.Empty:
                return
            except:  # no-coverage
                self.__logger.log(exc_string())

    def latest_logs(self):
        return self.__logger.msgs

    def last_recent_moni(self):
        return self.__recent_moni.popleft()

    def num_msgs_recvd(self):
        return self.__num_msgs_recvd

    def next_msg(self):
        try:
            return self.__latest_msgs.popleft()
        except IndexError:
            return None

    def wait_with_wakeup(self, f, timeout=1):
        def done():
            self.recv_thread.wakeup()
            return f()
        wait_until(done, timeout=timeout)


def main():  # no-coverage
#    parser = argparse.ArgumentParser(
#        epilog='Usage: "lbnecontrol <lbne_db_server>".')
#    parser.add_argument('--db', type=str, default='localhost',
#                        help="Name of LBNE DB server.")
#    args = parser.parse_args()
#    lbnedbserver = args.db
    with Control(logpath=os.path.join(os.environ["HOME"], ".lbnerc.log"),
                 poll_period=0.1, lbnedb_host=None,
                 web_host='dune-moni.umd.edu'):
        wait_for_interrupt()
