

def get_config_info_base(self):

    config_dirname = "/home/jcfree/standalone_daq_config/"

    ffp = []
    ffp.append( "%s/%s" % (config_dirname, self.config))
    ffp.append( "%s/common_code" % (config_dirname))

    return config_dirname, ffp
