
import os
import stat
import subprocess
from subprocess import Popen
import traceback

def save_run_record_base(self):

    # Save the FHiCL documents which were used to initialize the
    # artdaq processes

    outdir = self.tmp_run_record

    try:
        os.mkdir(outdir)
    except Exception:
        self.print_log("Exception raised during creation of %s ; this may occur because %s already exists, in which case this is not an error" % (outdir, outdir))

    if not os.path.exists(outdir):
        self.alert_and_recover("Problem creating output "
                               "directory " + outdir)
        return

    for procinfo in self.procinfos:

        if procinfo.host == "localhost":
            procinfo_host_to_record = os.environ["HOSTNAME"]
        else:
            procinfo_host_to_record = procinfo.host

        outf = open(outdir + "/" + procinfo.name + "_" +
                    procinfo_host_to_record + "_" +
                    procinfo.port + ".fcl", "w")

        outf.write(procinfo.fhicl_used)
        outf.close()

    # For good measure, let's also save the DAQInterface configuration file

    config_saved_name = "config.txt"

    Popen("cp -p " + self.config_filename + " " + outdir +
          "/" + config_saved_name,
          shell=True, stdout=subprocess.PIPE).wait()

    if not os.path.exists(outdir + "/" + config_saved_name):
        self.alert_and_recover("Problem creating file %s/%s" %
                               (outdir, config_saved_name))

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

    # Now save the commit hashes we determined during
    # initialization

    for pkg in sorted(self.package_hash_dict.keys()):
        outf.write("%s commit: %s\n" % (pkg, self.package_hash_dict[ pkg ] ))

    if self.pmt_host == "localhost":
        pmt_host_to_record = os.environ["HOSTNAME"]
    else:
        pmt_host_to_record = self.pmt_host

    outf.write("\n")
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
