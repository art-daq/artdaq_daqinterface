
import os
import re
import string

import subprocess
from subprocess import Popen

def expand_environment_variable_in_string(line):

    res = re.search(r"^(.*)(\$[A-Z]+)(.*)", line)

    if res:
        environ_var = res.group(2)
        environ_var = environ_var.strip("${}")

        if environ_var in os.environ.keys():
            line = res.group(1) + os.environ[ environ_var ] + res.group(3)
        else:
            raise Exception("Expanding line \"%s\", unable to find definition for environment variable \"%s\"" % \
                                (line.strip(), environ_var))

    return line

def make_paragraph(userstring, chars_per_line=75):
    userstring.strip()

    string_index = chars_per_line
    previous_string_index = -1
    ignore_algorithm = False

    userstring = string.replace(userstring, "\n", " ")

    while len(userstring) - string_index > 0:

        if not ignore_algorithm:
            while not userstring[string_index].isspace():
                string_index -= 1
                assert string_index >= 0
        else:
            while not userstring[string_index].isspace():
                string_index += 1
                if len(userstring) <= string_index:
                    return "\n" + userstring

        userstring = userstring[:string_index] + "\n" + userstring[string_index+1: ]

        string_index += chars_per_line

        # If there's a token with no whitespace which is longer
        # than chars_per_line characters (as may be the case with
        # some full pathnames, e.g.) there's a risk of an infinite
        # loop without the external logic below

        if previous_string_index == string_index:
            ignore_algorithm = True

        previous_string_index = string_index

    return "\n" + userstring

# JCF, 3/11/15

# "get_pids" is a simple utility function which will go to the
# requested host (defaults to the local host), and searches for a
# process by grep-ing for the passed greptoken in the process
# table returned by "ps aux". It returns a (possibly empty) list
# of the process IDs found

def get_pids(greptoken, host="localhost"):

    cmd = 'ps aux | grep "%s" | grep -v grep' % (greptoken)

    if host != "localhost":
        cmd = "ssh -f " + host + " '" + cmd + "'"

    proc = Popen(cmd, shell=True, stdout=subprocess.PIPE)

    lines = proc.stdout.readlines()

    pids = [line.split()[1] for line in lines]

    return pids

def table_range(fhiclstring, tablename):

    loc = string.find(fhiclstring, tablename)

    if loc == -1:
        return (-1, -1)

    open_brace_loc = string.index(fhiclstring[loc:], "{")

    close_braces_needed = 1
    close_brace_loc = -1

    for i_char, char in enumerate(fhiclstring[(loc+open_brace_loc+1):]):
        #print char

        if char == '{':
            close_braces_needed += 1
        elif char == '}':
            close_braces_needed -= 1

        #print close_braces_needed, i_char

        if close_braces_needed == 0:
            close_brace_loc = i_char
            break

    if close_brace_loc == -1:
        raise Exception(
            "Unable to find close brace for requested table \"%s\"" % \
                tablename)

    return (loc, loc + open_brace_loc + 1 + close_brace_loc + 1)


def commit_check_throws_if_failure(packagedir, commit_hash, date, request_after):

    assert os.path.exists( packagedir ), "Directory %s doesn't appear to exist; a check should occur earlier in the program for this" % (packagedir)

    cmds = []
    cmds.append("cd " + packagedir )
    cmds.append("git log | grep %s" % (commit_hash))

    proc = Popen(";".join(cmds), shell=True,
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proclines = proc.stdout.readlines()

    if request_after and len(proclines) != 1:
        raise Exception("Unable to find expected git commit hash %s (%s) in directory \"%s\"; this means the version of code in that directory isn't the one expected" % (commit_hash, date, packagedir))
    elif not request_after and len(proclines) != 0:
        raise Exception("Unexpectedly found git commit hash %s (%s) in directory \"%s\"; this means the version of code in that directory isn't the one expected" % (commit_hash, date, packagedir))


def main():

    sample_string = "Set this string to whatever string you want to pass to make_paragraph() for testing purposes"

    paragraphed_string=make_paragraph( sample_string )

    print
    print "Sample string: "
    print sample_string

    print
    print "Paragraphed string: "
    print paragraphed_string

if __name__ == "__main__":
    main()

