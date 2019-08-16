# JCF, Apr-20-2017

# For this module to work, you'll first need to have set up the
# artdaq-database in the shell environment

import os
import sys
sys.path.append( os.environ["ARTDAQ_DAQINTERFACE_DIR"] )

dbdirs = [dbdir for dbdir in os.environ["PYTHONPATH"].split(":") if "/artdaq_database/" in dbdir]
assert len(dbdirs) == 1, "More than one path in $PYTHONPATH appears to be an artdaq-database path"
sys.path.append(dbdirs[0] + "/../bin")

import subprocess
from subprocess import Popen
from rc.control.deepsuppression import deepsuppression
from rc.control.utilities import make_paragraph
from rc.control.utilities import fhiclize_document
import shutil
from shutil import copyfile

import re
import os
import string
import shutil

from rc.control.utilities import expand_environment_variable_in_string
from conftool import exportConfiguration
from conftool import getListOfAvailableRunConfigurations
from conftool import getListOfAvailableRunConfigurationsSubtractMasked
from conftool import archiveRunConfiguration
from conftool import updateArchivedRunConfiguration

def config_basedir(self):
    return "/tmp/database/"

def get_config_info_base(self):

    basedir = os.getcwd()

    ffp = []

    uuidgen=Popen("uuidgen", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip()
    tmpdir = config_basedir(self) + uuidgen

    Popen("mkdir -p %s" % tmpdir, shell=True).wait()
    os.chdir( tmpdir )

    tmpflagsfile = "%s/flags.fcl" % (tmpdir)
    with open(tmpflagsfile, "w") as outf:
        outf.write("flag_inactive:true\n")

    for subconfig in self.subconfigs_for_run:

        if subconfig not in getListOfAvailableRunConfigurations():
            raise Exception(make_paragraph("Error: (sub)config \"%s\" was not found in a call to conftool.getListOfAvailableRunConfigurations" % (subconfig)))
        elif subconfig not in getListOfAvailableRunConfigurationsSubtractMasked():
            raise Exception(make_paragraph("Error: (sub)config \"%s\" appears to have been masked off (i.e., it doesn't appear in a call to conftool.getListOfAvailableRunConfigurationsSubtractMasked given the flags file %s)" % (subconfig, tmpflagsfile)))

        subconfigdir = "%s/%s" % (tmpdir, subconfig)
        os.mkdir( subconfigdir )
        os.chdir( subconfigdir )
        
        with deepsuppression(self.debug_level < 2):
            result = exportConfiguration( subconfig )

            if not result:
                raise Exception("Error: the exportConfiguration function with the argument \"%s\" returned False" % \
                                subconfig)

        for dirname, dummy, dummy in os.walk( subconfigdir ):
            ffp.append( dirname )

        # DAQInterface doesn't like duplicate files with the same basename
        # in the collection of subconfigurations, and schema.fcl isn't used
        # since DAQInterface just wants the FHiCL documents used to initialize
        # artdaq processes...
        for dirname, dummy, filenames in os.walk( subconfigdir ):
            if "schema.fcl" in filenames:
                os.unlink("%s/schema.fcl" % (dirname))

    os.unlink(tmpflagsfile)
    os.chdir( basedir )
    return tmpdir, ffp


def put_config_info_base(self):

    scriptdir = os.environ["ARTDAQ_DAQINTERFACE_DIR"] + "/utils"

    if not os.path.exists( scriptdir ):
        raise Exception("Error in %s: unable to find script directory \"%s\"; should be in the base directory of the package" % (put_config_info_base.__name__, scriptdir))

    runnum = str(self.run_number)
    runrecord = self.record_directory + "/" + runnum

    tmpdir = "/tmp/" + Popen("uuidgen", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip()

    cmds = []
    cmds.append(" scriptdir=" + scriptdir)
    cmds.append( "mkdir " + tmpdir)
    cmds.append( "cd " + tmpdir)
    cmds.append( "cp -rp " + runrecord + " . ")
    cmds.append( "chmod 777 " + runnum )
    cmds.append( "cat " + runnum + "/metadata.txt | awk -f $scriptdir/fhiclize_metadata_file.awk > " + runnum + "/metadata.fcl" )
    cmds.append( "cat " + runnum + "/boot.txt | awk -f $scriptdir/fhiclize_boot_file.awk > " + runnum + "/boot.fcl" )
    cmds.append( "cat " + runnum + "/known_boardreaders_list.txt | awk -f $scriptdir/fhiclize_known_boardreaders_list_file.awk > " + runnum + "/known_boardreaders_list.fcl")
    cmds.append( "rm -f " + runnum + "/*.txt")

    if os.getenv("ARTDAQ_DATABASE_CONFDIR") is None:
        raise Exception(make_paragraph("Environment variable ARTDAQ_DATABASE_CONFDIR needs to be set in order for DAQInterface to determine where to find the schema.fcl file needed to archive configurations to the database; since ARTDAQ_DATABASE_CONFDIR is not set this may indicate that the version of artdaq_database you're using is old"))

    cmds.append("cp -p %s/schema.fcl ." % os.environ["ARTDAQ_DATABASE_CONFDIR"])

    status = Popen( "; ".join( cmds ), shell=True).wait()

    for filename in [tmpdir, "%s/%s" % (tmpdir, runnum), "%s/%s/metadata.fcl" % (tmpdir, runnum)] :
        assert os.path.exists( filename ), "%s is unexpectedly missing" % (filename)

    if status != 0:
        raise Exception("Problem during execution of the following:\n %s" % "\n".join(cmds))

    with open( "%s/%s/DataflowConfiguration.fcl" % (tmpdir, runnum), "w" ) as dataflow_file:

        with open( "%s/%s/boot.fcl" % (tmpdir, runnum) ) as boot_file:
            for line in boot_file.readlines():
                
                ignore_line = False

                for procname in ["EventBuilder", "DataLogger", "Dispatcher", "RoutingMaster"] :
                    res = re.search(r"^\s*%s_" % (procname), line)
                    if res:
                        ignore_line = True
                        break

                if "debug_level" in line or line == "":
                    ignore_line = True

                if not ignore_line:
                    dataflow_file.write("\n" + line)

        proc_attrs = ["host", "port", "label", "rank"]
        proc_types = ["BoardReader", "EventBuilder", "DataLogger", "Dispatcher", "RoutingMaster"]

        proc_line = {}

        with open("%s/ranks.txt" % (runrecord)) as ranksfile:
            for line in ranksfile.readlines():
                res = re.search(r"^\s*(\S+)\s+([0-9]+)\s+(\S+)\s+([0-9]+)\s*$", line)
                if res:
                    host, port, label, rank = res.group(1), res.group(2), res.group(3), res.group(4)
                    
                    for procinfo in self.procinfos:
                        if label == procinfo.label:
                            assert host == procinfo.host or (procinfo.host == "localhost" and host == os.environ["HOSTNAME"])
                            assert port == procinfo.port

                            # "host" used for the check, but could just as well be "port", "label" or "rank"
                            if "%s_host" % (procinfo.name) not in proc_line.keys():
                                for proc_attr in proc_attrs:
                                    proc_line["%s_%s" % (procinfo.name, proc_attr)] = "%s_%ss: [" % (procinfo.name, proc_attr)
                            
                            proc_line["%s_host" % (procinfo.name)] += "\"%s\"," % (procinfo.host)
                            proc_line["%s_port" % (procinfo.name)] += "\"%s\"," % (procinfo.port)
                            proc_line["%s_label" % (procinfo.name)] += "\"%s\"," % (procinfo.label)
                            proc_line["%s_rank" % (procinfo.name)] += "\"%s\"," % (rank)

        for proc_line_key, proc_line_value in proc_line.items():
            proc_line_value = proc_line_value[:-1] # Strip the trailing comma
            proc_line[ proc_line_key ] = proc_line_value + "]"
            dataflow_file.write("\n" + proc_line[ proc_line_key ] )

        with open( "%s/%s/metadata.fcl" % (tmpdir, runnum) ) as metadata_file:
            for line in metadata_file.readlines():
                if "DAQInterface_start_time" not in line and "DAQInterface_stop_time" not in line and not line == "":
                    dataflow_file.write("\n" + line)

    with open( "%s/%s/RunHistory.fcl" % (tmpdir, runnum), "w" ) as runhistory_file:
        runhistory_file.write("\nrun_number: %s" % (runnum))
        
        with open( "%s/%s/metadata.fcl" % (tmpdir, runnum) ) as metadata_file:
            for line in metadata_file.readlines():
                if "config_name" in line:
                    runhistory_file.write("\n" + line)
                elif "components" in line:
                    runhistory_file.write("\n" + line)

        if os.environ["DAQINTERFACE_PROCESS_MANAGEMENT_METHOD"] == "external_run_control" and \
           os.path.exists("/tmp/info_to_archive_partition%d.txt" % (self.partition_number)):
            runhistory_file.write( fhiclize_document( "/tmp/info_to_archive_partition%d.txt" % (self.partition_number) ) )

    basedir=os.getcwd()
    os.chdir( tmpdir )

    with deepsuppression(self.debug_level < 2):
        subconfigs_for_run = [subconfig.replace("/","_") for subconfig in self.subconfigs_for_run]
        result = archiveRunConfiguration( "_".join(subconfigs_for_run), runnum )

    if not result:
        raise Exception(make_paragraph("There was an error attempting to archive the FHiCL documents (temporarily saved in %s); this may be because of an issue with the schema file, %s/schema.fcl, such as an unlisted fragment generator" % (tmpdir, os.environ["ARTDAQ_DATABASE_CONFDIR"])))

    os.chdir( basedir )

    res = re.search(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", tmpdir)
    assert res, "Unable to find uuidgen-generated temporary directory, will perform no deletions"

    shutil.rmtree( tmpdir )

    return

def put_config_info_on_stop_base(self):

    if os.environ["DAQINTERFACE_PROCESS_MANAGEMENT_METHOD"] != "external_run_control" or \
       not os.path.exists("/tmp/info_to_archive_partition%d.txt" % (self.partition_number)):
        return

    runnum = str(self.run_number)
    tmpdir = "/tmp/" + Popen("uuidgen", shell=True, stdout=subprocess.PIPE).stdout.readlines()[0].strip()
    os.mkdir(tmpdir)
    os.mkdir("%s/%s" % (tmpdir, runnum))
    os.chdir(tmpdir)


    with open( "%s/%s/RunHistory2.fcl" % (tmpdir, runnum), "w" ) as runhistory_file:
        runhistory_file.write( fhiclize_document( "/tmp/info_to_archive_partition%d.txt" % (self.partition_number ) ))

    copyfile("%s/schema.fcl" % (os.environ["ARTDAQ_DATABASE_CONFDIR"]), "%s/schema.fcl" % (tmpdir))

    with deepsuppression():
        subconfigs_for_run = [subconfig.replace("/","_") for subconfig in self.subconfigs_for_run]
        result = updateArchivedRunConfiguration( "_".join(subconfigs_for_run), runnum )

    if not result:
        raise Exception(make_paragraph("There was an error attempting to archive the FHiCL documents (temporarily saved in %s); this may be because of an issue with the schema file, %s/schema.fcl, such as an unlisted fragment generator" % (tmpdir, os.environ["ARTDAQ_DATABASE_CONFDIR"])))


    res = re.search(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", tmpdir)
    assert res, "Unable to find uuidgen-generated temporary directory, will perform no deletions"

    os.chdir("/tmp")
    shutil.rmtree( tmpdir )

def listdaqcomps_base(self):
    assert False, "%s not yet implemented" % (listdaqcomps_base.__name__)

def listconfigs_base(self):
    print
    print "Available configurations: "

    config_cntr = 0

    with open("/tmp/listconfigs_" + os.environ["USER"] + ".txt", "w") as outf:
        for config in getListOfAvailableRunConfigurations():
            config_cntr += 1

            if config_cntr <= self.max_configurations_to_list:
                outf.write(config + "\n")
                print config

def main():

    listconfigs_test = False
    get_config_info_test = True
    put_config_info_test = False

    if listconfigs_test:
        print "Calling listconfigs_base"
        listconfigs_base("ignored_argument")
        
    if get_config_info_test:
        print "Calling get_config_info_base"

        class MockDAQInterface:
            subconfigs_for_run = [ "ToyComponent_EBwriting00019", "np04_WibsReal_Ssps_BeamTrig_CRT_00001" ]
            debug_level = 2

        mydir, mydirs = get_config_info_base( MockDAQInterface() )

        print "FHiCL directories to search: " + " ".join(mydirs)
        print "Directory where the FHiCL documents are located: " + mydir

    if put_config_info_test:
        print "Calling put_config_info_base"

        class MockDAQInterface:
            run_number = 73
            record_directory = "/daq/artdaq/run_records/"
            config_for_run = "push_pull_testing"

        put_config_info_base( MockDAQInterface() )

if __name__ == "__main__":
    main()
