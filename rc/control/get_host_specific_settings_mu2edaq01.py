
def get_host_specific_settings_base(self):
    self.log_directory = "/tmp"
    self.record_directory = "/home/jcfree/run_records"
    self.daq_setup_script = "setupARTDAQDEMO"

    self.package_hashes_to_save = ["artdaq-demo", "artdaq-core-demo", "artdaq" ]

