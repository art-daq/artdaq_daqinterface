"""

Unit tests relating directly to lbnecontrol.

"""

import time
import random
import datetime

from rc.control.processes import (start_control, kill_control,
                                  control_pid_file, control_running)
from rc.control.component import Component
from rc.compatibility import nested
from rc.control.cmd import lbnecmd
from rc.control.control import Control
from rc.io import sender, receiver
from rc.threading import threaded
from rc.util import (eq, raises, isin, isnotin, file_cleanup,
                     wait_until, andn, is_mac, complement)


def succeeds(d):
    assert d["succeeded"], d["reason"]


def test_control_context():
    isin("Connection refused", lbnecmd("check"))
    with Control(web_host='localhost'):
        isin("lbnecontrol: Available", lbnecmd("check"))


def test_command_help():
    isin("Usage", lbnecmd("help"))


def test_unknown_command():
    with Control(web_host='localhost'):
        isin("Unknown command", lbnecmd("shunyata"))


def test_start_stop_control():
    cpf = control_pid_file()
    with file_cleanup(cpf):
        assert not control_running()
        start_control(None)
        assert control_running()
        kill_control()
        assert not control_running()


def test_sending_to_control_can_get_messages():
    with Control(web_host='localhost') as control:
        with sender() as s:
            s.send({"data": "is good"})

            def done():
                return control.next_msg()

            control.wait_with_wakeup(done)


def test_many_senders_all_in_one_thread_to_control():
    N = 4 if is_mac() else 40
    with Control(web_host='localhost') as control:
        with nested(*[sender() for _ in range(N)]) as senders:
            for i, s in enumerate(senders):
                s.send({"sender": i})

            def done():
                return control.num_msgs_recvd() == N

            control.wait_with_wakeup(done)


def test_many_senders_in_separate_threads_to_control(long=False):
    NUM_SENDERS = 10
    NUM_MSGS = 100 if long else 3
    PAYLOAD = "X" * (100000 if long else 100)

    def thread_target(i):
        with sender() as s:
            for m in range(NUM_MSGS):
                s.send({"sender": i,
                        "payload": PAYLOAD,
                        "msg": m})

    t = time.time()
    with Control(logpath="/tmp/__control_log",web_host='localhost') as control:
        with nested(*[threaded(target=thread_target, args=(i,))
                      for i in range(NUM_SENDERS)]):
            recvd = []

            def consume_msgs():
                while True:
                    m = control.next_msg()
                    if m:
                        recvd.append(m)
                    else:
                        return

            def done():
                consume_msgs()
                if recvd:
                    assert andn(*[m["payload"] == PAYLOAD for m in recvd])
                return len(recvd) == NUM_SENDERS * NUM_MSGS
            control.wait_with_wakeup(done,
                                     timeout=NUM_SENDERS * NUM_MSGS * .05)

    dt = time.time() - t
    bytes = len(PAYLOAD) * NUM_SENDERS * NUM_MSGS
    if long:
        print ("%d bytes in %s seconds (%.2f MB/s)"
               % (bytes, dt, bytes / (1000. * 1000. * max(dt, 1))))


def test_control_logs_are_recorded():
    with Control(web_host='localhost') as control:
        assert len(control.latest_logs()) > 0


def test_control_msgs_are_recorded():
    with Control(web_host='localhost') as control:
        eq(control.num_msgs_recvd(), 0)
        with sender() as s:
            s.send({"sender": "cryo",
                    "payload": '"some data"'})
            control.wait_with_wakeup(lambda: control.next_msg())


def test_no_initial_components():
    with Control(web_host='localhost') as control:
        eq(control.components(), [])


def control_has_component(control, name):
    return name in map(lambda c: c["name"], control.components())


def test_component_with_no_init():
    with Control(web_host='localhost') as control:
        with Component(name="noinit", rpc_port=6659, skip_init=True):
            control.wait_with_wakeup(lambda: control_has_component(control,
                                                                   "noinit"))
            eq(control.component_state("noinit"), "ready")
            control.change_component_state("noinit", "starting")
            control.wait_with_wakeup(
                lambda: control.component_state("noinit") == "running")
            isin("running", lbnecmd("check noinit"))


def test_component_registration_with_control():
    with Control(web_host='localhost') as control:
        with Component(name="nondaq", rpc_port=6659):
            control.wait_with_wakeup(lambda: control_has_component(control,
                                                                   "nondaq"))
            eq(control.component_state("nondaq"), "stopped")
            control.change_component_state("nondaq", "initializing")
            control.change_component_state("nondaq", "starting")
            control.wait_with_wakeup(
                lambda: control.component_state("nondaq") == "running")
            isin("running", lbnecmd("check nondaq"))
            # Check general 'check' syntax:
            eq('running',
               [l.split(' ')[2]
                for l in lbnecmd("check").split('\n')
                if l.startswith('nondaq')][0])
            control.change_component_state("nondaq", "stopping")
            wait_until(lambda: control.component_state("nondaq") == "ready")


def test_check_for_good_bad_transitions():
    with Control(web_host='localhost') as control:
        with Component(name="comp", rpc_port=6665):
            # Check in the stopped state.
            present = lambda: control_has_component(control, "comp")
            control.wait_with_wakeup(present)
            isin("comp not in one of",
                 lbnecmd("start comp"))
            isin("comp not in one of",
                 lbnecmd("stop comp"))
            isin("comp not in one of",
                 lbnecmd("terminate comp"))
            isin("comp not in one of",
                 lbnecmd("pause comp"))
            isin("comp not in one of",
                 lbnecmd("resume comp"))
            #  OK, now move to "ready" and try others
            isin("OK", lbnecmd("init comp"))
            isin("comp not in one of",
                 lbnecmd("init comp"))
            isin("comp not in one of",
                 lbnecmd("stop comp"))
            isin("comp not in one of",
                 lbnecmd("pause comp"))
            isin("comp not in one of",
                 lbnecmd("resume comp"))
            #  OK, now move to "running" and try others
            isin("OK", lbnecmd("start comp"))
            isin("comp not in one of",
                 lbnecmd("init comp"))
            isin("comp not in one of",
                 lbnecmd("start comp"))
            isin("comp not in one of",
                 lbnecmd("terminate comp"))
            isin("comp not in one of",
                 lbnecmd("resume comp"))
            #  OK, now move to "paused" and try others
            isin("OK", lbnecmd("pause comp"))
            isin("comp not in one of",
                 lbnecmd("init comp"))
            isin("comp not in one of",
                 lbnecmd("start comp"))
            isin("comp not in one of",
                 lbnecmd("terminate comp"))
            isin("comp not in one of",
                 lbnecmd("pause comp"))
            # Check ability to stop from paused or started
            isin("OK", lbnecmd("stop comp"))
            isin("OK", lbnecmd("start comp"))
            isin("OK", lbnecmd("stop comp"))


def test_component_deregistration_and_reregistration():
    with Control(web_host='localhost') as control:
        with Component(name="comp", rpc_port=6661):
            present = lambda: control_has_component(control, "comp")
            absent = complement(present)
            control.wait_with_wakeup(present)

            isin("'control' expects name",  # ...
                 lbnecmd("control blahblah"))

            isin("'control' expects name",  # ...
                 lbnecmd("control comp localhost 6661 nonsyncronoooous"))

            # Make sure we complain about controlling already-known component:
            isin("is already being controlled",
                 lbnecmd("control comp localhost 6661 asynchronous"))
            # Make sure a nonexistent component on the same port is flagged:
            isin("doesn't answer",
                 lbnecmd("control noncomp localhost 6661 asynchronous"))
            # Make sure unknown component gets reported:
            isin("not in the list", lbnecmd("ignore foo"))
            # Forceably ignore component:
            eq("OK", lbnecmd("ignore comp"))
            assert absent()
            # re-control it:
            eq("OK", lbnecmd("control comp localhost 6661 asynchronous"))
            assert present()
            # Start it, ignore it, and fail to re-control it:
            succeeds(control.change_component_state("comp", "starting"))
            eq("OK", lbnecmd("ignore comp"))
            isin("is not in the stopped or paused state",
                 lbnecmd("control comp localhost 6661 asynchronous"))


def test_ignore_multiple_components():
    with Control(web_host='localhost') as control:
        with Component(name='c1', rpc_port=6661):
            with Component(name='c2', rpc_port=6662):
                control.wait_with_wakeup(lambda: (len(control.components()) ==
                                                  2))
                eq("OK", lbnecmd("ignore c1 c2"))
                eq(len(control.components()), 0)


def test_unknown_component():
    with Control(web_host='localhost'):
        isin("unknown", lbnecmd("check missiles"))


def test_multiple_component_workflow():
    N = 3
    with Control(web_host='localhost') as control:
        with(nested(*[Component(name="comp%d" % d, rpc_port=6660 + d)
                      for d in range(N)])):

            def all_components_controlled():
                return len(control.components()) == N
            control.wait_with_wakeup(all_components_controlled)

            def getstates():
                chk = control.check(["comp%d" % ic
                                     for ic in range(N)])
                return set(c["state"] for c in chk["components"])

            eq(set(["stopped"]), getstates())

            for ic in range(N):
                isin("comp%d@localhost:666%d (asynchronous): stopped" %
                     (ic, ic), lbnecmd("check"))

            isin("foo is unknown", lbnecmd("start foo"))

            for ic in range(N):
                eq("OK", lbnecmd("init comp%d" % ic))

            def all_components_running():
                return set(["ready"]) == getstates()

            for ic in range(N):
                eq("OK", lbnecmd("start comp%d" % ic))

            def all_components_running():
                return set(["running"]) == getstates()

            control.wait_with_wakeup(all_components_running)

            isin("comp0 not in one of", lbnecmd("start comp0"))

            # Use alt syntax for stop:
            eq("OK", lbnecmd("stop " + ' '.join(["comp%d" % ic
                                                 for ic in range(N)])))


def test_component_reregistration():
    with Control(web_host='localhost') as control:
        with Component(name="daq1", rpc_port=6666):
            control.wait_with_wakeup(lambda: len(control.components()) == 1)
        # Reregister:
        with Component(name="daq1", rpc_port=6667):

            def have_new_port():
                comps = control.components()
                assert len(comps) == 1
                return comps[0]["port"] == 6667

            control.wait_with_wakeup(have_new_port)


def test_mulitple_component_registrations():
    with Control(web_host='localhost') as control:
        wait = control.wait_with_wakeup
        with Component(name="cmp1", rpc_port=6666):
            wait(lambda: len(control.components()) == 1)
            with Component(name="cmp2", rpc_port=6667):
                wait(lambda: len(control.components()) == 2)
                eq("OK", lbnecmd("init cmp1"))
                eq("OK", lbnecmd("init cmp2"))
                eq("OK", lbnecmd("start cmp1"))
                eq("OK", lbnecmd("start cmp2"))
                wait(lambda: control.component_state("cmp1") == "running")
                wait(lambda: control.component_state("cmp2") == "running")
                with Component(name="cmp3", rpc_port=6668):
                    wait(lambda: len(control.components()) == 3)
                    lbnecmd("init cmp3")
                    lbnecmd("start cmp3")
                    wait(lambda: control.component_state("cmp3") == "running")
                    control.change_component_state('cmp1', 'stopping')
                    control.change_component_state('cmp2', 'stopping')
                    control.change_component_state('cmp3', 'stopping')
                    wait(lambda: control.component_state("cmp1") == "ready")
                    wait(lambda: control.component_state("cmp2") == "ready")
                    wait(lambda: control.component_state("cmp3") == "ready")


def test_init_and_start_return_runparams():
    with Control(web_host='localhost') as control:
        wait = control.wait_with_wakeup
        with Component(name="cmp1", rpc_port=6666, synchronous=True) as comp:
            wait(lambda: len(control.components()) == 1)
            lbnecmd("init daq")
            isin("config", comp.run_params.keys())
            lbnecmd("start daq")
            isin("run_number", comp.run_params.keys())


def test_control_sends_moni_data_to_mock_web_ui():
    with nested(Control(web_host='localhost'),
                sender(),
                receiver(port=7000)) as (control, s, mock_web):
        moni = {"type": "moni",
                "service": "testmoni",
                "t": str(datetime.datetime.utcnow()),
                "varname": "x",
                "value": random.random() * 1000}
        s.send(moni)

        def done():
            recvd = mock_web.recv_nonblock()
            if recvd is None:
                return False
            return recvd.get("payload", None) == moni

        control.wait_with_wakeup(done)


def test_component_sends_data():
    with Control(web_host='localhost') as control:
        with Component(name="cmp", rpc_port=6666) as comp:
            control.wait_with_wakeup(lambda: len(control.components()) == 1)
            raises(IndexError, control.last_recent_moni)
            control.change_component_state('cmp', 'starting')
            control.wait_with_wakeup(
                lambda: control.component_state("cmp") == "running")

            def running_state_moni(m):
                return (m["type"] == "moni" and
                        m["varname"] == "state" and
                        m["value"] == "running")

            def simulated_quantity(m):
                return (m["type"] == "moni" and
                        m["varname"] == "x")

            monis = []

            def got_running_message():
                try:
                    monis.append(control.last_recent_moni())
                except IndexError:
                    return False

                if any(m for m in monis if running_state_moni(m)):
                    return True

            control.wait_with_wakeup(got_running_message)

            def got_simulated_quantity():
                comp.wakeup()
                try:
                    monis.append(control.last_recent_moni())
                except IndexError:
                    return False

                if any(m for m in monis if simulated_quantity(m)):
                    return True

            control.wait_with_wakeup(got_simulated_quantity)


def test_component_cannot_be_named_daq():
    def make_daq():
        with Component(name='daq'):
            pass
    raises(ValueError, make_daq)


def test_synchronous_component_cannot_be_started_alone():
    with Control(web_host='localhost') as control:
        with Component(name='daq1', rpc_port=6666, synchronous=True):
            control.wait_with_wakeup(lambda: len(control.components()) == 1)
            raises(ValueError,
                   control.change_component_state, 'daq1', 'starting')
            isin("cannot change state on its own",
                 control.start(["daq1"])["reason"])


def test_synchronous_and_asynchronous_cannot_start_together():
    with nested(Control(web_host='localhost'),
                Component(name='daq1', rpc_port=6666, synchronous=True),
                Component(name='cryo', rpc_port=6667, synchronous=False)) \
            as (control, daq1, cryo):
        control.wait_with_wakeup(lambda: len(control.components()) == 2)
        isin("Cannot change DAQ state alongside asynchronous components",
             control.start(["daq", "cryo"])["reason"])


def test_synchronous_components_start_and_stop_together():
    with nested(Control(web_host='localhost'),
                Component(name='daq1', rpc_port=6666, synchronous=True),
                Component(name='daq2', rpc_port=6667, synchronous=True)) \
            as (control, daq1, daq2):
        control.wait_with_wakeup(lambda: len(control.components()) == 2)

        succeeds(control.initialize(["daq"]))
        succeeds(control.start(["daq"]))

        def daqs_are_in_state(state):
            daq1.wakeup()
            daq2.wakeup()
            return daq1.state("daq1") == daq2.state("daq2") == state

        control.wait_with_wakeup(lambda: daqs_are_in_state("running"))

        succeeds(control.stop(["daq"]))
        control.wait_with_wakeup(lambda: daqs_are_in_state("ready"))
        succeeds(control.terminate(["daq"]))
        control.wait_with_wakeup(lambda: daqs_are_in_state("stopped"))


def test_check_shows_components_synchrony_type():
    with Control(web_host='localhost') as control:
        with Component(name='daq1', rpc_port=6666,
                       synchronous=True):
            with Component(name='cmp2', rpc_port=6667,
                           synchronous=False):
                control.wait_with_wakeup(
                    lambda: len(control.components()) == 2)
                comps = control.check()["components"]
                synchronies = [c["synchronous"] for c in comps]
                eq(set([True, False]), set(synchronies))


def test_high_component_control_port_numbers():
    """
    Regression for Issue #34: Giving a component a high port number
    hoses `lbnecmd check`
    """
    raises(ValueError, Component, name='daq1', rpc_port=66666)


def test_handle_disappearing_component():
    """
    Regression for Issue #20: lbnecontrol check returns error if a
    registered component is no longer running.
    """
    with Control(web_host='localhost') as control:
        with Component(name='daq1', rpc_port=6666,
                       synchronous=True):
            control.wait_with_wakeup(
                lambda: len(control.components()) == 1)

        def state():
            return control.check()["components"][0]["state"]

        control.wait_with_wakeup(lambda: state() == "missing")
        lbnecmd("ignore daq1")
        assert "missing" not in control.check()


def test_unknown_state():
    """
    Make sure control barfs when given a bad state
    """
    with Control(web_host='localhost') as control:
        with Component(name='comp', rpc_port=6666,
                       synchronous=False):
            control.wait_with_wakeup(
                lambda: len(control.components()) == 1)
            raises(Exception,
                   control.change_component_state, "comp", "badstate")


def test_can_pause_async_component():
    """
    Support 'pause' state of generic component
    """
    with Control(web_host='localhost') as control:
        with Component(name='comp', rpc_port=6666,
                       synchronous=False):
            control.wait_with_wakeup(
                lambda: len(control.components()) == 1)
            eq("OK", lbnecmd("init comp"))
            control.wait_with_wakeup(
                lambda: control.component_state("comp") == "ready")
            eq("OK", lbnecmd("start comp"))
            control.wait_with_wakeup(
                lambda: control.component_state("comp") == "running")
            eq("OK", lbnecmd("pause comp"))
            control.wait_with_wakeup(
                lambda: control.component_state("comp") == "paused")
            eq("OK", lbnecmd("resume comp"))


def test_bad_command():
    with Control(web_host='localhost'):
        isin("Unknown command", lbnecmd("adfadsfasdf"))


def test_check_shows_config_and_run_number():
    with Control(web_host='localhost') as control:
        with Component(name='daq1', rpc_port=6666,
                       synchronous=True):
            control.wait_with_wakeup(
                lambda: len(control.components()) == 1)

            # Run number shouldn't be shown before run
            isnotin("Run number", lbnecmd("check"))

            # Start DAQ; run number should be 1
            eq("OK", lbnecmd("init daq"))
            eq("OK", lbnecmd("start daq"))
            control.wait_with_wakeup(
                lambda: control.component_state("daq1") == "running")
            c = lbnecmd("check")
            isin("Run number: ", c)
            isin("Run configuration: ", c)
            # (will allow user to set config later...)

            # Stop DAQ
            eq("OK", lbnecmd("stop daq"))
            control.wait_with_wakeup(
                lambda: control.component_state("daq1") == "ready")

            # Again, should not see run number
            isnotin("Run number", lbnecmd("check"))

            # Start again, run number should be there
            eq("OK", lbnecmd("start daq"))
            control.wait_with_wakeup(
                lambda: control.component_state("daq1") == "running")
            isin("Run number: ", lbnecmd("check"))


def test_set_list_configs():
    with Control(web_host='localhost') as control:
        isin("Available configs", lbnecmd("listconfigs"))
        isin("dummy : Dummy description", lbnecmd("listconfigs"))
        isin("Config not found in CfgMgr: junk",
             lbnecmd("setconfig junk"))
        isin("OK", lbnecmd("setconfig dummy"))
        with Component(name='daq1', rpc_port=6661,
                       synchronous=True):
            control.wait_with_wakeup(
                lambda: len(control.components()) == 1)
            eq("OK", lbnecmd("init daq"))
            isin("daq not in the stopped state",
                 lbnecmd("setconfig dummy2"))
            eq("OK", lbnecmd("start daq"))
            control.wait_with_wakeup(
                lambda: control.component_state("daq1") == "running")
            c = lbnecmd("check")
            isin("Run configuration: dummy", c)
            isin("daq not in the stopped state",
                 lbnecmd("setconfig dummy2"))


def test_set_list_daqcomps():
    with Control(web_host='localhost') as control:
        isin('Available', lbnecmd("listdaqcomps"))
        isin('Selected', lbnecmd("listdaqcomps"))
        isin("not in list of available DAQcomponents",
             lbnecmd("setdaqcomps fred"))
        isin("OK", lbnecmd("setdaqcomps RCE01"))
        with Component(name='daq1', rpc_port=6661,
                       synchronous=True):
            control.wait_with_wakeup(
                lambda: len(control.components()) == 1)
            eq("OK", lbnecmd("init daq"))
            isin("daq not in the stopped state",
                 lbnecmd("setdaqcomps bob"))
            eq("OK", lbnecmd("start daq"))
            control.wait_with_wakeup(
                lambda: control.component_state("daq1") == "running")
            isin("daq not in the stopped state",
                 lbnecmd("setdaqcomps jenny"))

def test_addrm_daqcomps():
    print "blah"
    with Control(web_host='localhost') as control:
        isin('Available', lbnecmd("listdaqcomps"))
        isin('Selected', lbnecmd("listdaqcomps"))
        isin("not in selected DAQcomponents",
            lbnecmd("rmdaqcomps RCE01 bob"))
        isin("OK", lbnecmd("setdaqcomps RCE01"))
        isin("OK", lbnecmd("adddaqcomps RCE01"))
        isin("OK", lbnecmd("adddaqcomps RCE02"))
        isin("OK", lbnecmd("rmdaqcomps RCE01"))
        isin("not in list of available",
            lbnecmd("adddaqcomps bob"))
def test_set_list_run_type():
    with Control(web_host='localhost') as control:
        isin("Test", lbnecmd("listruntype"))
        isin("specify", lbnecmd("setruntype"))
        isin("OK", lbnecmd("setruntype Physics"))
        isin("OK", lbnecmd("setruntype Commissioning"))
        isin("Commissioning", lbnecmd("listruntype"))
        isin("OK", lbnecmd("setruntype physics"))
        isin("OK", lbnecmd("setruntype PHYSICS"))
        isin("OK", lbnecmd("setruntype pHySiCs"))
        isin("not in allowed list", lbnecmd("setruntype testing"))
        with Component(name='daq1', rpc_port=6661,
                       synchronous=True):
            control.wait_with_wakeup(
                lambda: len(control.components()) == 1)
            eq("OK", lbnecmd("init daq"))
            isin("daq not in the stopped state",
                 lbnecmd("setruntype physics"))
            eq("OK", lbnecmd("start daq"))
            control.wait_with_wakeup(
                lambda: control.component_state("daq1") == "running")
            isin("daq not in the stopped state",
                 lbnecmd("setruntype physics"))
