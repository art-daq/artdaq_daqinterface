
import os

def get_config_info_base(self):

    config_dirname = os.getcwd() + "/simple_test_config"

    if not os.path.exists( config_dirname ):
        self.alert_and_recover("Error: unable to find expected directory of FHiCL configuration files \"%s\"; " + \
                                   "this probably means you're not running out of DAQInterface's base directory" )

    ffp = []
    ffp.append( "%s/%s" % (config_dirname, self.config_for_run))
    ffp.append( "%s/common_code" % (config_dirname))

    return config_dirname, ffp

# put_config_info_base should be a no-op 

def put_config_info_base(self):
    pass
