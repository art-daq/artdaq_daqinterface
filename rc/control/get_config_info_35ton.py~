

def get_config_info_base(self):

    # See if the configuration manager is actually running

    cfgservername = "CfgMgrApp"

    # Tack on whitespace so we guard against mixing up edits of
    # CfgMgrApp.cc with actual running of the executable

    greptoken = cfgservername + " "

    cmd = 'ps aux | grep "' + greptoken + '" | grep -v grep '

    proc = Popen(cmd, shell=True, stdout=subprocess.PIPE)
    cfg_lines = proc.stdout.readlines()

    self.num_config_procs = len(cfg_lines)

    if self.num_config_procs != 1:
        self.print_log("Error in DAQInterface: expected one "
                       "(and only one) instance of %s running" %
                       (cfgservername))
        self.alert_and_recover("Either no configuration server or "
                               "more than one server found running")
        return "", []

    token1, token2 = cfg_lines[0].split()[-2:]

    if token1 != cfgservername:
        self.alert_and_recover("Problem checking the "
                               "configuration server: expected "
                               "\"%s\" but got %s" %
                               (cfgservername, token1))
    config_dirname = token2

    ffp = []
    ffp.append( "%s/%s" % (config_dirname, self.run_params["config"]))
    ffp.append( "%s/common_code" % (config_dirname))

    # JCF, 12/2/14

    # At Giles's request, make sure the program fails if it sees
    # edits have been made since the last configuration directory
    # commit. Also, make it fail if it sees the most recent
    # configuration wasn't pushed to the central repo

    # JCF, 2/6/15

    # As discussed at meetings this past Monday and Thursday,
    # allow for a "development" mode where frequent changes to the
    # configurations take place; this is accomplished by making it
    # possible to disable the failure mode described above in the
    # 12/2/14 comment

    cmds = []
    cmds.append("cd %s" % config_dirname)
    cmds.append("git diff HEAD --name-status %s" % self.run_params["config"] )

    proc = Popen("; ".join(cmds), shell=True, stdout=subprocess.PIPE)
    status_lines = proc.stdout.readlines()

    # If no edits have been made in the configuration
    # subdirectory, there should be no output from the above
    # command

    if not self.disable_configuration_check and \
            len(status_lines) > 0:
        print
        print "Unclean working configuration directory %s/%s found, " \
            "output of \"git status\" is: " % \
            (config_dirname, self.run_params["config"])

        for line in status_lines:
            print line,

            self.alert_and_recover("Unclean working configuration "
                                   "directory")
            return "", []

    # JCF, 12/2/14

    # Now check that the commits to the configuration directory
    # have been pushed to the central repo

    cmds = []
    cmds.append("cd %s" % config_dirname)
    cmds.append("git diff origin/master --name-status %s" % self.run_params["config"])

    proc = Popen("; ".join(cmds), shell=True, stdout=subprocess.PIPE)
    diff_lines = proc.stdout.readlines()

    if not self.disable_configuration_check and \
            len(diff_lines) > 0:
        print
        print "Difference between configuration directory %s/%s " \
            "and central repository found, " \
            "output of \"git diff origin/master --name-status %s\" is: " % \
            (config_dirname, self.run_params["config"], self.run_params["config"])

        for line in diff_lines:
            print line,

        self.alert_and_recover("Difference between configuration "
                               "directory and central repository")
        return "", []
        
    return config_dirname, ffp

