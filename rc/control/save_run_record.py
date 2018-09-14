
import os
import stat
import re
import glob
import subprocess
from subprocess import Popen
from shutil import copyfile
import traceback
from rc.control.utilities import make_paragraph

def save_run_record_base(self):

    # Save the FHiCL documents which were used to initialize the
    # artdaq processes

    outdir = self.tmp_run_record

    os.mkdir(outdir) 
    assert os.path.exists( outdir )

    # JCF, Jun-20-2018
    
    # protoDUNE-specific - you should NOT see this on the develop
    # branch: I write the FHiCL documents not just to the subdirectory
    # of /tmp/run_record_attempted_np04daq, which ensures that the
    # correct run record is saved, but also to
    # /tmp/run_record_attempted_np04daq itself, so that the interface
    # with JCOP isn't broken. Notice that it's far less likely that
    # another partition will clobber the documents in
    # /tmp/run_record_attempted_np04daq between when DAQInterface
    # creates them and JCOP picks them up, than when DAQInterface
    # creates them and they get saved on run start - in this
    # best-of-both-worlds approach, JCOP can continue using
    # /tmp/run_record_attempted_np04daq while we can still be
    # confident the correct run record is saved

    # JCF, Sep-13-2018

    # Two additions:

    # (1) I'm writing not just the FHiCL documents, but also
    # metadata.txt, so that RC can access it and save it in the root
    # file via the put_config_info_archive function in artdaq

    # (2) I'm now writing out to a third area,
    # /tmp/run_record_attempted_np04daq/<RC partition>, to allay fears
    # of clobbering from other partitions in use

    old_outdir = "/tmp/run_record_attempted_%s" % (os.environ["USER"])
    assert os.path.exists( old_outdir )

    partition_outdir = "/tmp/run_record_attempted_%s/%d" % (os.environ["USER"], self.partition_number_rc)
    assert os.path.exists( partition_outdir )

    if not self.manage_processes:
        globs = ["*.fcl", "metadata.txt"]

        for oldfiles in [ glob.glob( "%s/%s" % (rcdir, fileglob)) for rcdir in [old_outdir, partition_outdir] for fileglob in globs ]:
            for oldfile in oldfiles:
                os.unlink(oldfile)

    for procinfo in self.procinfos:
        
        if not self.manage_processes:
            outdirs = [ old_outdir, outdir, partition_outdir ]
        else:
            outdirs = [ outdir ]

        for outd in outdirs:
            outf = open(outd + "/" + procinfo.label + ".fcl", "w")

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

    if not self.manage_processes:
        copyfile("/tmp/info_to_archive_partition%d.txt" % (self.partition_number_rc), \
                 "%s/rc_info.txt" % (outdir))

        if not os.path.exists("%s/rc_info.txt" % (outdir)):
            self.alert_and_recover(make_paragraph("Problem copying /tmp/info_to_archive_partition%d.txt into %s/rc_info.txt; does original file exist?" % (self.partition_number_rc, outdir)))

    # JCF, 11/20/14

    # Now save "metadata" about the run in the
    # "metadata_r<run #>.txt" file. This includes the
    # selected configuration, selected components, and commit
    # hashes of lbne-artdaq and lbnerc

    # JCF, Dec-4-2016: changed to metadata.txt, as this is executed
    # before the start transition

    metadata_basename = "metadata.txt"

    outf = open(outdir + "/" + metadata_basename, "w")

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
                     ("routingmaster", self.routingmaster_log_filenames),
                     ("aggregator", self.aggregator_log_filenames)]

        for logtuple in logtuples:

            outf.write("\n")
            outf.write("\n%s logfiles: " % logtuple[0])

            for filename in logtuple[1]:
                outf.write("\n" + filename)

    outf.write("\n")
    outf.close()

    if not self.manage_processes:
        for rcdir in [old_outdir, partition_outdir]:
            copyfile(outdir + "/" + metadata_basename, rcdir + "/" + metadata_basename)

    ranksfile = "%s/ranks.txt" % (outdir)
    if not self.manage_processes:
        ranksfile_rc = "/tmp/ranks%d.txt" % (self.partition_number_rc)
        if os.path.exists( ranksfile_rc ):
            copyfile( ranksfile_rc, ranksfile )
        else:
            raise Exception(make_paragraph("Unable to find expected ranks file produced by RC, \"%s\"" % (ranksfile_rc)))
    else:
        with open(ranksfile, "w") as outfile:
            outfile.write("        host   port         procName  rank\n")
            outfile.write("\n")

            rank = 0

            with open(self.pmtconfigname) as infile:
                for line in infile.readlines():
                    res = re.search(r"^[A-Za-z]+!([^!]+)", line)
                    assert res
                    host = res.group(1)

                    res = re.search(r"\s*id\s*:\s*([0-9]+)", line)
                    assert res
                    port = res.group(1)

                    res = re.search(r"\s*application_name\s*:\s*([^\s]+)", line)
                    assert res
                    label = res.group(1)

                    outfile.write("%s\t%s\t%s\t%d\n" % (host, port, label, rank))
                    rank += 1

            outfile.close()


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

