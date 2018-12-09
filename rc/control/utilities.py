
import os
import re
import string
import socket

import subprocess
from subprocess import Popen

from time import sleep

from multiprocessing.pool import ThreadPool

bash_unsetup_command="upsname=$( which ups ); if [[ -n $upsname ]]; then unsetup() { . `$upsname unsetup \"$@\"` ; }; for pp in `printenv | sed -ne \"/^SETUP_/{s/SETUP_//;s/=.*//;p}\"`; do test $pp = UPS && continue; prod=`echo $pp | tr \"A-Z\" \"a-z\"`; unsetup -j $prod; done; echo \"After bash unsetup, products active (should be nothing but ups listed):\"; ups active; else echo \"ups does not appear to be set up; will not unsetup any products\"; fi"

def expand_environment_variable_in_string(line):

    res = re.search(r"^(.*)(\$[A-Z][A-Z_0-9]*)(.*)", line)

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

# [Comment added by KAB, 17-Apr-2018]
# This function returns the contents of the FHiCL table that immediately
# follows the specified string (tablename).  It does not require that
# 'tablename' actually be a FHiCL key.
def table_range(fhiclstring, tablename, startingloc=0):

    # 13-Apr-2018, KAB: added the startingloc argument so that this function can
    # be used to find more than the first instance of the tablename in the string.
    loc = string.find(fhiclstring, tablename, startingloc)

    if loc == -1:
        return (-1, -1)

    open_brace_loc = string.index(fhiclstring[loc:], "{")

    close_braces_needed = 1
    close_brace_loc = -1

    for i_char, char in enumerate(fhiclstring[(loc+open_brace_loc+1):]):

        if char == '{':
            close_braces_needed += 1
        elif char == '}':
            close_braces_needed -= 1

        if close_braces_needed == 0:
            close_brace_loc = i_char
            break

    if close_brace_loc == -1:
        raise Exception(
            "Unable to find close brace for requested table \"%s\"" % \
                tablename)

    return (loc, loc + open_brace_loc + 1 + close_brace_loc + 1)

# 17-Apr-2018, KAB: added this function to find the *enclosing* FHiCL
# table for the specified string. This can be useful when looking for
# a table that has a desirable FHiCL value, and we want to fetch the
# contents of the entire table.
def enclosing_table_range(fhiclstring, searchstring, startingloc=0):

    loc = string.find(fhiclstring, searchstring, startingloc)

    if loc == -1:
        return (-1, -1)

    open_brace_loc = string.rindex(fhiclstring, "{", startingloc, loc)

    close_braces_needed = 1
    close_brace_loc = -1

    for i_char, char in enumerate(fhiclstring[(open_brace_loc+1):]):

        if char == '{':
            close_braces_needed += 1
        elif char == '}':
            close_braces_needed -= 1

        if close_braces_needed == 0:
            close_brace_loc = i_char
            break

    if close_brace_loc == -1:
        raise Exception(
            "Unable to find close brace for requested table \"%s\"" % \
                searchstring)

    return (open_brace_loc + 1, open_brace_loc + close_brace_loc + 1)

# 26-Nov-2018, ELF: This function finds the name of the enclosing table
# for the specified string. This is used when determining which
# destinations block is currently being filled during bookkeeping.
def enclosing_table_name(fhiclstring, searchstring, startingloc=0):

    loc = string.find(fhiclstring, searchstring, startingloc)
    if loc == -1:
        return "notfound"

    open_brace_loc = string.rindex(fhiclstring, "{", 0, loc)

    while string.rfind(fhiclstring, '}', open_brace_loc, loc) != -1:
        loc = open_brace_loc - 1
        open_brace_loc = string.rindex(fhiclstring, "{", 0, loc)

    colon_loc = string.rindex(fhiclstring, ":", 0, open_brace_loc)

    while fhiclstring[colon_loc - 1] == " ":
        colon_loc -= 1

    name = re.sub('.*\s', "", fhiclstring[:colon_loc])

    return name

def commit_check_throws_if_failure(packagedir, commit_hash, date, request_after):

    assert os.path.exists( packagedir ), "Directory %s doesn't appear to exist; a check should occur earlier in the program for this" % (packagedir)

    cmds = []
    cmds.append("cd " + packagedir )
    cmds.append("git log | grep %s" % (commit_hash))

    proc = Popen(";".join(cmds), shell=True,
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proclines = proc.stdout.readlines()

    if request_after and len(proclines) != 1:
        raise Exception(make_paragraph("Unable to find expected git commit hash %s (%s) in directory \"%s\"; this means the version of code in that directory isn't the one expected" % (commit_hash, date, packagedir)))
    elif not request_after and len(proclines) != 0:
        raise Exception(make_paragraph("Unexpectedly found git commit hash %s (%s) in directory \"%s\"; this means the version of code in that directory isn't the one expected" % (commit_hash, date, packagedir)))

def is_msgviewer_running():
    
    tty = Popen("tty", shell=True,
                     stdout=subprocess.PIPE).stdout.readlines()[0].strip()

    if "/dev/" in tty:
        tty = string.replace(tty, "/dev/", "")

    for line in Popen("ps u", shell=True, 
                      stdout=subprocess.PIPE).stdout.readlines():
        if "msgviewer" in line and tty in line:
            return True

    return False

def execute_command_in_xterm(home, cmd):
    
    if not os.path.exists( os.environ["HOME"] + "/.Xauthority"):
        raise Exception("Unable to find .Xauthority file in home directory")

    if home != os.environ["HOME"]:
        status = Popen("cp -p ~/.Xauthority %s" % (home), shell=True).wait()
        if status != 0:
            raise Exception("Unable to copy .Xauthority file into directory %s; do you have write permissions there?" % (home))


    # JCF, May-11-2017

    # The following chant to xterm is influenced both by Ron's
    # implementation of xt_cmd.sh in artdaq-demo as well as the info
    # found at
    # https://superuser.com/questions/363614/leave-xterm-open-after-task-is-complete

    fullcmd = "env -i SHELL=/bin/bash PATH=/usr/bin:/bin LOGNAME=%s USER=%s  DISPLAY=%s  REALHOME=%s HOME=%s KRB5CCNAME=%s  xterm -geometry 100x33+720+0 -sl 2500 -e \"%s ; read \" &" % (os.environ["LOGNAME"], os.environ["USER"], os.environ["DISPLAY"], os.environ["HOME"], \
                                                                                                                                                                                              home, os.environ["KRB5CCNAME"], cmd)

    Popen(fullcmd, shell=True).wait()

def date_and_time():
    return Popen("LC_ALL=\"en_US.UTF-8\" date", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip()

def construct_checked_command(cmds):

    checked_cmds = []

    for cmd in cmds:
        
        checked_cmds.append( cmd )

        if not re.search(r"\s*&\s*$", cmd) and not bash_unsetup_command in cmd:
            check_cmd = "if [[ \"$?\" != \"0\" ]]; then echo %s: Nonzero return value from the following command: \"%s\" >> /tmp/daqinterface_checked_command_failures.log; exit 1; fi " % (date_and_time(), cmd)
            checked_cmds.append( check_cmd )

    total_cmd = " ; ".join( checked_cmds )

    return total_cmd


def reformat_fhicl_documents(setup_fhiclcpp, input_fhicl_strings):

    if not os.path.exists( setup_fhiclcpp ):
        raise Exception(make_paragraph("Expected fhiclcpp setup script %s doesn't appear to exist" % (setup_fhiclcpp)))

    cmd = "grep -c ^processor /proc/cpuinfo"

    nprocessors = Popen(cmd, shell=True,
                        stdout=subprocess.PIPE).stdout.readlines()[0].strip()

    if not re.search(r"^[0-9]+$", nprocessors):
        raise Exception(make_paragraph("A problem occurred when DAQInterface tried to execute \"%s\"; result was not an integer" % (cmd)))

    pool = ThreadPool(int(nprocessors))

    preformat_filenames=[ Popen("mktemp", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip() for i in range(len(input_fhicl_strings))]
    postformat_filenames=[ Popen("mktemp", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip() for i in range(len(input_fhicl_strings))]

    for preformat_filename, input_fhicl_string in zip(preformat_filenames, input_fhicl_strings):
        with open(preformat_filename, "w") as preformat_file:
            preformat_file.write(input_fhicl_string)

    def reformat_subset_of_documents(indices):

        cmds = []
        cmds.append("if [[ -z $( command -v fhicl-dump ) ]]; then %s; source %s; fi" % \
                    (bash_unsetup_command, setup_fhiclcpp))
        cmds.append("which fhicl-dump")
        for index in indices:
            cmds.append("fhicl-dump -l 0 -c %s -o %s" % \
                        (preformat_filenames[index], postformat_filenames[index]))

        fullcmd = construct_checked_command( cmds )

        status = Popen(fullcmd, shell = True).wait()

        exception_message = ""
        formatted_fhicl_strings = []

        if status != 0:
            exception_message = make_paragraph("Failure in attempt of %s to reformat a FHiCL document; nonzero status returned. This may indicate either a problem with the setup file %s or a problem with the FHiCL code itself" % (reformat_subset_of_documents.__name__, setup_fhiclcpp))

        for index in indices:
            if os.path.exists( postformat_filenames[index] ):
                formatted_fhicl_strings.append( open( postformat_filenames[index] ).read() )
                os.unlink( postformat_filenames[index] )
            else:
                exception_message = make_paragraph("Failure in %s: problem creating postformat file in fhicl-dump call" % (reformat_subset_of_documents.__name__))

        if exception_message != "":
            raise Exception( exception_message )

        for index in indices:
            os.unlink( preformat_filenames[index] )

        return formatted_fhicl_strings   # End of reformat_subset_of_documents()

        
    document_set_size = 8
    num_total_documents = len(input_fhicl_strings)

    if num_total_documents > document_set_size:
        document_sets = [ range(i, i+document_set_size) for i in range(0, num_total_documents, document_set_size) if i+document_set_size < num_total_documents]
        remainder_set = range( document_sets[-1][-1] + 1, num_total_documents)

        if len(remainder_set) > 0:
            document_sets.append( remainder_set )
    else:
        document_sets = [ range(num_total_documents) ]

    postformat_fhicl_document_lists = pool.map(reformat_subset_of_documents, document_sets)

    return [ postformat_fhicl_document for postformat_fhicl_document_list in postformat_fhicl_document_lists \
                  for postformat_fhicl_document in postformat_fhicl_document_list ]

# JCF, 12/2/14

# Given the directory name of a git repository, this will return
# the most recent hash commit in the repo

def get_commit_hash(gitrepo):

    if not os.path.exists(gitrepo):
        return "Unknown"

    cmds = []
    cmds.append("cd %s" % (gitrepo))
    cmds.append("git log | head -1 | awk '{print $2}'")

    proc = Popen(";".join(cmds), shell=True,
                 stdout=subprocess.PIPE)
    proclines = proc.stdout.readlines()

    if len(proclines) != 1 or len(proclines[0].strip()) != 40:
        raise Exception(make_paragraph("Commit hash for \"%s\" not found; this was requested in the \"packages_hashes_to_save\" list found in %s" % (gitrepo, os.environ["DAQINTERFACE_SETTINGS"])))

    return proclines[0].strip()

def get_commit_comment( gitrepo ):
    
    max_length = 50
    
    if not os.path.exists(gitrepo):
        return ""

    cmds = []
    cmds.append("cd %s" % (gitrepo))
    cmds.append("git log --format=%B -n 1 HEAD")
    proc = Popen(";".join(cmds), shell=True,
                 stdout=subprocess.PIPE)
    single_line_comment = " ".join( proc.stdout.readlines() )

    for badchar in [ '\n', '"', "'" ]:
        single_line_comment = single_line_comment.replace(badchar, "")

    if len(single_line_comment) > max_length:
        single_line_comment = single_line_comment[0:max_length] + "..."

    return single_line_comment
        
def fhicl_writes_root_file(fhicl_string):

    # 17-Apr-2018, KAB: added the MULTILINE flag to get this search to behave as desired.
    # 30-Aug-2018, KAB: added support for RootDAQOutput

    if ( "RootOutput" in fhicl_string or "RootDAQOut" in fhicl_string ) and \
       re.search(r"^\s*fileName\s*:\s*.*\.root", fhicl_string, re.MULTILINE):
        return True
    else:
        return False

def obtain_messagefacility_fhicl():

    if "DAQINTERFACE_MESSAGEFACILITY_FHICL" in os.environ.keys():
        messagefacility_fhicl_filename = os.environ["DAQINTERFACE_MESSAGEFACILITY_FHICL"]
    else:
        messagefacility_fhicl_filename = os.getcwd() + "/MessageFacility.fcl" 

    # JCF, 10-25-2018

    # The FHiCL controlling messagefacility messages below is
    # embedded by artdaq within other FHiCL code (see
    # artdaq/DAQdata/configureMessageFacility.cc in artdaq
    # v2_03_03 for details).

    default_contents = """ 

# This file was automatically generated as %s at %s on host %s, and is
# the default file DAQInterface uses to determine how to modify the
# standard MessageFacility configuration found in artdaq-core
# v3_02_01's configureMessageFacility.cc file. You can edit the
# contents below to change the behavior of how/where MessageFacility
# messages are sent, though keep in mind that this FHiCL will be
# nested inside a table. Or you can use a different file by setting
# the environment variable DAQINTERFACE_MESSAGEFACILITY_FHICL to the
# name of the other file.

udp : { type : "UDP" threshold : "DEBUG"  port : 30000 host : "%s" } 

""" % (messagefacility_fhicl_filename, date_and_time(), os.environ["HOSTNAME"], socket.gethostname())
        
    if not os.path.exists( messagefacility_fhicl_filename ):
        with open(messagefacility_fhicl_filename, "w") as outf_mf:
            outf_mf.write( default_contents )

    return messagefacility_fhicl_filename


def main():

    paragraphed_string_test = False
    msgviewer_check_test = False
    execute_command_in_xterm_test = False
    reformat_fhicl_document_test = False
    bash_unsetup_test = True

    if paragraphed_string_test:
        sample_string = "Set this string to whatever string you want to pass to make_paragraph() for testing purposes"

        paragraphed_string=make_paragraph( sample_string )

        print
        print "Sample string: "
        print sample_string

        print
        print "Paragraphed string: "
        print paragraphed_string

    if msgviewer_check_test:
        if is_msgviewer_running():
            print "A msgviewer appears to be running"
        else:
            print "A msgviewer doesn't appear to be running"
        
    if execute_command_in_xterm_test:
        execute_command_in_xterm(os.environ["PWD"], "echo Hello world")
        execute_command_in_xterm(os.environ["PWD"], "echo You should see an xclock appear; xclock ")

    if reformat_fhicl_document_test:
        assert False, "This test is deprecated until function signature is brought up-to-date"
        inputstring = 'mytable: {   this: "and"        that: "and  the other"   }'
        source_filename = Popen("mktemp", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip()

        # Note the setup string assumes cvmfs is available...
        proddir = "/cvmfs/fermilab.opensciencegrid.org/products/artdaq"
        print "This test assumes that %s is available" % (proddir)

        with open(source_filename, "w") as source_file:
            source_file.write( "source %s/setup; setup fhiclcpp v4_05_01 -q prof:e14" % (proddir) )

        outputstring = "Not set"
        try:
            outputstring = reformat_fhicl_document(source_filename, inputstring)
        except Exception:
            print "Exception caught"

        os.unlink(source_filename)

        print "Input FHiCL string: "
        print inputstring
        print
        print "Output FHiCL string: "
        print outputstring
        print

    if bash_unsetup_test:
        Popen( bash_unsetup_command, shell=True)

if __name__ == "__main__":
    main()

