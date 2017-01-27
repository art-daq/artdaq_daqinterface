
import os
import re
import traceback

import sys
sys.path.append( os.getcwd() )

from rc.control.utilities import expand_environment_variable_in_string

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

def get_daqinterface_config_info_base(self, daqinterface_config_filename):

    inf = open(daqinterface_config_filename)

    if not inf:
        raise Exception(self.make_paragraph(
                            "Exception in DAQInterface: " +
                            "unable to locate configuration file \"" +
                            daqinterface_config_filename + "\""))

    memberDict = {"name": None, "host": None, "port": None, "fhicl": None}

    for line in inf.readlines():

        line = expand_environment_variable_in_string( line )

        # Is this line a comment?
        res = re.search(r"^\s*#", line)
        if res:
            continue

        res = re.search(r"\s*PMT host\s*:\s*(\S+)", line)
        if res:
            self.pmt_host = res.group(1)
            continue

        res = re.search(r"\s*PMT port\s*:\s*(\S+)", line)
        if res:
            self.pmt_port = res.group(1)
            continue

        res = re.search(r"\s*DAQ directory\s*:\s*(\S+)",
                        line)
        if res:
            self.daq_dir = res.group(1)
            continue

        res = re.search(r"\s*debug level\s*:\s*(\S+)",
                        line)
        if res:
            self.debug_level = int(res.group(1))
            continue

        if "EventBuilder" in line or "Aggregator" in line:

            res = re.search(r"\s*(\w+)\s+(\S+)\s*:\s*(\S+)", line)

            if not res:
                raise Exception("Exception in DAQInterface: "
                                "problem parsing " + daqinterface_config_filename)

            memberDict["name"] = res.group(1)
            memberDict[res.group(2)] = res.group(3)

            # Has the dictionary been filled s.t. we can use it to
            # initalize a procinfo object?

            # JCF, 11/13/14

            # Note that if the configuration manager is running,
            # then we expect the AggregatorMain applications to
            # have a host and port specified in config.txt, but
            # not a FHiCL document

            # JCF, 3/19/15

            # Now, we also expect only a host and port for
            # EventBuilderMain applications as well

            filled = True

            for label, value in memberDict.items():
                if value is None and not label == "fhicl":
                    filled = False

            # If it has been filled, then initialize a Procinfo
            # object, append it to procinfos, and reset the
            # dictionary values to null strings

            if filled:
                self.procinfos.append(self.Procinfo(memberDict["name"],
                                                    memberDict["host"],
                                                    memberDict["port"]))
                for varname in memberDict.keys():
                    memberDict[varname] = None

    return daqinterface_config_filename

def listdaqcomps_base(self):

    components_file = os.getcwd() + "/.components.txt"

    try:
        inf = open( components_file )
    except:
        print traceback.format_exc()
        return 

    lines = inf.readlines()

    print
    print "# of components found in listdaqcomps call: %d" % (len(lines))

    lines.sort()
    for line in lines:
        component = line.split()[0].strip()
        host = line.split()[1].strip()
        
        print "%s (runs on %s)" % (component, host)

def main():
    print "Calling listdaqcomps_base: "
    listdaqcomps_base("ignored_argument")

if __name__ == "__main__":
    main()
