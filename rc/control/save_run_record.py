
import os
import stat
import re
import subprocess
from subprocess import Popen
import traceback
from rc.control.utilities import make_paragraph


def save_run_record_base(self):

    # Save the FHiCL documents which were used to initialize the
    # artdaq processes

    outdir = self.tmp_run_record

    try:
        os.makedirs(outdir)
    except Exception:
        raise Exception(make_paragraph("Exception raised during creation of %s" % (outdir)))
        return


    if not os.path.exists(outdir):
        raise Exception("Problem creating output directory %s" % (outdir))
        return

    for procinfo in self.procinfos:

        outf = open(outdir + "/" + procinfo.label + ".fcl", "w")

        outf.write(procinfo.fhicl_used)
        outf.close()

    # For good measure, let's also save the DAQInterface configuration file

    config_saved_name = "boot.txt"

    Popen("cp -p " + self.daqinterface_config_file + " " + outdir +
          "/" + config_saved_name,
          shell=True, stdout=subprocess.PIPE).wait()

    if not os.path.exists(outdir + "/" + config_saved_name):
        self.alert_and_recover("Problem creating file %s/%s" %
                               (outdir, config_saved_name))

    # As well as the DAQ setup script

    Popen("cp -p " + self.daq_setup_script + " " + outdir + 
          "/setup.txt", shell=True, stdout=subprocess.PIPE).wait()

    if not os.path.exists(outdir + "/setup.txt"):
        self.alert_and_recover("Problem creating file %s/setup.txt" % (outdir))

    assert os.path.exists( os.environ["DAQINTERFACE_KNOWN_BOARDREADERS_LIST"] )

    Popen("cp -p " + os.environ["DAQINTERFACE_KNOWN_BOARDREADERS_LIST"] +
          " " + outdir + "/known_boardreaders_list.txt", shell=True,
          stdout=subprocess.PIPE).wait()

    if not os.path.exists(outdir + "/known_boardreaders_list.txt"):
        self.alert_and_recover("Problem creating file " + outdir + "/known_boardreaders_list.txt")

    # JCF, 11/20/14

    # Now save "metadata" about the run in the
    # "metadata_r<run #>.txt" file. This includes the
    # selected configuration, selected components, and commit
    # hashes of lbne-artdaq and lbnerc

    # JCF, Dec-4-2016: changed to metadata.txt, as this is executed
    # before the start transition

    outf = open(outdir + "/metadata.txt", "w")

    outf.write("Config name: %s\n" % self.config_for_run)

    for i_comp, component in \
            enumerate(sorted(self.daq_comp_list)):
        outf.write("Component #%d: %s\n" % (i_comp, component))

    outf.write("DAQInterface directory: %s\n" % ( os.getcwd() ))

    # Now save the commit hashes we determined during
    # initialization

    if "ARTDAQ_DAQINTERFACE_VERSION" in os.environ.keys():
        outf.write("DAQInterface commit: %s\n" % ( os.environ["ARTDAQ_DAQINTERFACE_VERSION"] ) )
    else:
        outf.write("DAQInterface commit: %s\n" % ( self.get_commit_hash(os.environ["ARTDAQ_DAQINTERFACE_DIR"]) ) )

    for pkg in sorted(self.package_hash_dict.keys()):
        outf.write("%s commit: %s\n" % (pkg, self.package_hash_dict[ pkg ] ))

    if self.pmt_host == "localhost":
        pmt_host_to_record = os.environ["HOSTNAME"]
    else:
        pmt_host_to_record = self.pmt_host

    outf.write("\n")

    if self.manage_processes:
        outf.write("\npmt logfile(s): %s:%s/pmt/%s" %
                   (pmt_host_to_record, self.log_directory,
                    self.log_filename_wildcard))

        logtuples = [("boardreader", self.boardreader_log_filenames),
                     ("eventbuilder", self.eventbuilder_log_filenames),
                     ("aggregator", self.aggregator_log_filenames)]

        for logtuple in logtuples:

            outf.write("\n")
            outf.write("\n%s logfiles: " % logtuple[0])

            for filename in logtuple[1]:
                outf.write("\n" + filename)

    outf.write("\n")
    outf.close()

    if self.debug_level >= 2:
        print "Saved run configuration records in %s" % \
            (outdir)
        print

def total_events_in_run_base(self):

    # JCF, Apr-19-2018
    # This function will need to be rewritten to work, thus the assert False
    
    assert False

    data_logger_filenames = []
    
    if len(self.aggregator_log_filenames) > 0:

        for log_filename in self.aggregator_log_filenames:
            host, filename = log_filename.split(":")
        
            cmd = "grep -l \"is_data_logger\s*=\s*1\" " +  filename

            if host != "localhost" and host != os.environ["HOSTNAME"]:
                cmd = "ssh -f " + host + " '" + cmd + "'"
            
            proc = Popen(cmd, shell=True, stdout=subprocess.PIPE)
            proclines = proc.stdout.readlines()
            
            if len(proclines) != 0:
                assert len(proclines) == 1, "%s\n%s\nETC." % (proclines[0], proclines[1])
                assert proclines[0].strip() == filename, "%s not the same as %s" % (proclines[0].strip(), filename)
            else:
                continue
                
            data_logger_filenames.append( log_filename )
    else:
        data_logger_filenames = self.eventbuilder_log_filenames

    total = 0
    fail_value = -999

    for log_filename in data_logger_filenames:
        host, filename = log_filename.split(":")

        cmd = "sed -r -n '/Subrun [0-9]+ in run " + str(self.run_number) + " has ended/s/.*There were ([0-9]+) events in this subrun.*/\\1/p' " + log_filename.split(":")[1]

        if host != "localhost" and host != os.environ["HOSTNAME"]:
            cmd = "ssh -f " + host + " \"" + cmd + "\""

        proc = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proclines = proc.stdout.readlines()

        proclines = [ line.strip() for line in proclines ]

        warning_msg = "WARNING: unable to deduce the number of events in run " + \
            str(self.run_number) + " by running the following command: \"" + \
            cmd + "\""

        if len(proclines) == 0:
            print warning_msg
            return fail_value

        for line in proclines:
            if not re.search(r"^[0-9]+$", line):
                print warning_msg
                return fail_value

        for line in proclines:
            total += int(line)
        
    return total

def save_metadata_value_base(self, key, value):

    outdir = "%s/%s" % (self.record_directory, str(self.run_number))
    assert os.path.exists(outdir + "/metadata.txt")

    outf = open(outdir + "/metadata.txt", "a")

    outf.write("\n%s: %s\n" % (key, value))

