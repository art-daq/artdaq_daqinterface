
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
        # outf = open(outdir + "/" + procinfo.name + "_" +
        #             procinfo.host + "_" +
        #             procinfo.port + "_r" +
        #             str(self.run_number_for_run) +
        #             ".fcl", "w")

        outf = open(outdir + "/" + procinfo.name + "_" +
                    procinfo.host + "_" +
                    procinfo.port + ".fcl", "w")

        outf.write(procinfo.fhicl_used)
        outf.close()

    # For good measure, let's also save the DAQInterface configuration file

#    config_saved_name = "config_r%d.txt" % (self.run_number_for_run)
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

#    outf = open(outdir + "/metadata_r" +
#                str(self.run_number_for_run) + ".txt", "w")

    outf = open(outdir + "/metadata.txt", "w")

    outf.write("Config name: %s\n" % self.config_for_run)

    for i_comp, component in \
            enumerate(sorted(self.daq_comp_list)):
        outf.write("Component #%d: %s\n" % (i_comp, component))

    # Now save the commit hashes we determined during
    # initialization

    for pkg in sorted(self.package_hash_dict.keys()):
        outf.write("%s commit: %s\n" % (pkg, self.package_hash_dict[ pkg ] ))

    outf.write("\n")
    outf.write("\npmt logfile(s): %s:%s/pmt/%s" %
               (self.pmt_host, self.log_directory,
                self.log_filename_wildcard))

    logtuples = [("boardreader", self.boardreader_log_filenames),
                 ("eventbuilder", self.eventbuilder_log_filenames),
                 ("aggregator", self.aggregator_log_filenames)]

    for logtuple in logtuples:

        outf.write("\n")
        outf.write("\n%s logfiles: " % logtuple[0])

        for filename in logtuple[1]:
            outf.write("\n%s:%s/%s/%s" % (self.pmt_host,
                                          self.log_directory,
                                          logtuple[0], filename))

    outf.write("\n")
    outf.close()

    if self.debug_level >= 1:
        print "Saved run configuration records in %s" % \
            (outdir)
        print

    # # Now that we're done creating the run record, remove write
    # # permissions from the records directory

    # os.chmod(self.record_directory, perms & (~stat.S_IWUSR))

    # # As well as the run record subdirectory

    # os.chmod(outdir, perms & (~stat.S_IWUSR))
