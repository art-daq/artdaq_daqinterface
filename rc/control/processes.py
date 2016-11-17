"""
"""

from rc.util import remove_if_exists
import os
import os.path
import signal
import subprocess


def pid_file(name):
    return "/tmp/lbne%s.pid" % name


def control_pid_file():
    return pid_file("control")


def pid_from_file(filename):
    try:
        with file(filename) as f:
            return int(f.read())
    except IOError:
        return None


def start_control(lbnedb_host):
    assert not pid_from_file(control_pid_file())
    if lbnedb_host:
        procstring = "lbnecontrol --db %s" % lbnedb_host[0]
    else:
        procstring = "lbnecontrol"
    pro = subprocess.Popen(procstring,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, shell=True,
                           preexec_fn=os.setsid)
    with file(control_pid_file(), "w") as f:
        print >> f, pro.pid


def kill_control():
    pid = pid_from_file(control_pid_file())
    os.killpg(pid, signal.SIGTERM)
    remove_if_exists(control_pid_file())


def control_running():
    return os.path.exists(control_pid_file())
