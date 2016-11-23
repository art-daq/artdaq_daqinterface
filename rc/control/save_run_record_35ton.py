
import os
import stat
import subprocess
from subprocess import Popen
import traceback

def save_run_record_base(self):

    # Save the FHiCL documents which were used to initialize the
    # artdaq processes

    outdir = self.record_directory + "/" + \
        str(self.run_params["run_number"])

    # First, check that the record directory is read-only; if it
    # isn't, publish a warning that it should be (this will help
    # prevent the potential disaster represented by the deletion
    # of the record directory

    perms = os.stat(self.record_directory)[stat.ST_MODE]

    if perms & stat.S_IWUSR:
        warnmsg = "Warning in DAQInterface: %s is not read-only;" \
            " to accomplish this for next time," \
            " execute \"chmod 555 %s\"" % \
            (self.record_directory, self.record_directory)
        self.print_log(warnmsg)

    os.chmod(self.record_directory, perms | stat.S_IWUSR)

    try:
        os.mkdir(outdir)
    except Exception:
        self.print_log("DAQInterface caught an exception " +
                       "in do_start_running()")
        self.print_log(traceback.format_exc())
        self.alert_and_recover("Problem creating "
                                   "output directory " + outdir)
        return

    if not os.path.exists(outdir):
        self.alert_and_recover("Problem creating output "
                               "directory " + outdir)
        return

    for procinfo in self.procinfos:
        outf = open(outdir + "/" + procinfo.name + "_" +
                    procinfo.host + "_" +
                    procinfo.port + "_r" +
                    str(self.run_params["run_number"]) +
                    ".fcl", "w")

        outf.write(procinfo.fhicl_used)
        outf.close()

    # For good measure, let's also save the DAQInterface configuration file

    config_saved_name = "config_r%d.txt" % (self.run_params["run_number"])

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

    outf = open(outdir + "/metadata_r" +
                str(self.run_params["run_number"]) + ".txt", "w")

    outf.write("Config name: %s\n" % self.run_params["config"])

    for i_comp, component in \
            enumerate(sorted(self.run_params["daq_comp_list"])):
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

    # JCF, Sep-22-2015

    # Save the defaults.xml file used in the rce code

    has_rces = False

    for component in self.run_params["daq_comp_list"] :
        if "rce" in component:
            has_rces = True

    # JCF, Sep-2-2016

    # You'll want to change the location of defaults.xml if you're
    # not running on the 35ton cluster

    if has_rces:
        cmd="scp -p lbnedaq3:/home/lbnedaq/cob_nfs/35ton/config/defaults.xml %s" % (outdir)
        Popen(cmd, shell=True).wait()

    if self.debug_level >= 1:
        print "Saved run configuration records in %s" % \
            (outdir)
        print

    # Now that we're done creating the run record, remove write
    # permissions from the records directory

    os.chmod(self.record_directory, perms & (~stat.S_IWUSR))

    # As well as the run record subdirectory

    os.chmod(outdir, perms & (~stat.S_IWUSR))
