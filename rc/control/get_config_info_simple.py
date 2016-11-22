

def get_config_info_base(self):

    config_dirname = "/home/nfs/dunedaq/daqarea/config/"

    ffp = []
    ffp.append( "%s/%s" % (config_dirname, self.run_params["config"]))
    ffp.append( "%s/common_code" % (config_dirname))

    return config_dirname, ffp
