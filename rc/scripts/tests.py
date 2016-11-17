import datetime
import subprocess
from rc.control.control import Control
from rc.util import eq, gt


def process(cmd):
    proc = subprocess.Popen(cmd.split(),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if err:  # no-coverage
        assert not err, err
    if out:  # no-coverage
        print out


def _do_cmd_test(value, typ, t=None, host=None):
    with Control(web_host='localhost') as control:
        if t is None:
            tstr = ""
        else:
            tstr = " -t " + "_".join(str(t).split(" "))

        if host is None:
            hstr = ""
        else:
            hstr = " -H " + host
        process("lbnemoni erik-office temp %s -T %s%s%s" %
                (value, typ, tstr, hstr))

        def done():
            m = control.next_msg()
            if m:
                if "t" not in m or type(m["t"]) is str:
                    return False
                if t is None:
                    gt(m["t"], datetime.datetime(2013, 1, 1))
                else:
                    eq(m["t"], t)
                eq(m["service"], "erik-office")
                eq(m["varname"], "temp")
                eq(m["value"], value)
                return True

        control.wait_with_wakeup(done)


def test_external_moni_program():
    _do_cmd_test("21.3", "str")
    _do_cmd_test(21.3, "float")
    _do_cmd_test(21, "int")
    _do_cmd_test(21, "int", t=datetime.datetime(2010, 1, 2, 3, 4, 5, 678))
    _do_cmd_test(21.3, "float", host="localhost")
