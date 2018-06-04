
import os
import sys
sys.path.append( os.environ["ARTDAQ_DAQINTERFACE_DIR"] )

import re
import traceback

from rc.control.utilities import expand_environment_variable_in_string
from rc.control.utilities import make_paragraph

def get_config_parentdir():
    parentdir = os.environ["DAQINTERFACE_FHICL_DIRECTORY"]
    assert os.path.exists(parentdir), "Expected configuration directory %s doesn't appear to exist" % (parentdir)
    return parentdir


def get_config_info_base(self):

    config_dirname = get_config_parentdir()
    config_dirname_subdir = config_dirname + "/" + self.config_for_run + "/"

    if not os.path.exists( config_dirname_subdir ):
        raise Exception(make_paragraph("Error: unable to find expected directory of FHiCL configuration files \"%s\"; this may mean you're not running out of DAQInterface's base directory" % (config_dirname_subdir) ))

    ffp = []
    ffp.append( config_dirname_subdir )
    ffp.append( "%s/common_code" % (config_dirname))

    return config_dirname_subdir, ffp

# put_config_info_base should be a no-op 

def put_config_info_base(self):
    pass

def check_members(self, memberDict, num_actual_processes):
    # Has the dictionary been filled s.t. we can use it to
    # initalize a procinfo object?
    filled = True
    for key, value in memberDict.items():
        if value is None and key != "fhicl" and key != "subsystem" and key != "label":
            filled = False

    # If it has been filled, then initialize a Procinfo
    # object, append it to procinfos, and reset the
    # dictionary values to null strings

    if memberDict["label"] == None and filled:
        memberDict["label"] = memberDict["name"]

    if filled:
        self.procinfos.append(self.Procinfo(memberDict["name"],
                                            memberDict["host"],
                                            memberDict["port"],
                                            memberDict["label"],
                                            memberDict["subsystem"],
                                            memberDict["fhicl"]))
        num_actual_processes += 1

        for varname in memberDict.keys():
            memberDict[varname] = None

    return num_actual_processes

def get_daqinterface_config_info_base(self, daqinterface_config_filename):

    inf = open(daqinterface_config_filename)

    if not inf:
        raise Exception(self.make_paragraph(
                            "Exception in DAQInterface: " +
                            "unable to locate configuration file \"" +
                            daqinterface_config_filename + "\""))

    memberDict = {"name": None, "label": None, "host": None, "port": None, "fhicl": None, "subsystem": None}
    subsystemDict = {"id": None, "source": None, "destination": None}

    num_expected_processes = 0
    num_actual_processes = 0

    for line in inf.readlines():

        line = expand_environment_variable_in_string( line )

        # Is this line a comment?
        # Check for complete program definitions on comment or blank lines
        res = re.search(r"^\s*#", line)
        if res:
            num_actual_processes = check_members(self, memberDict, num_actual_processes)
            continue

        res = re.search(r"^\s*$", line)
        if res:
            num_actual_processes = check_members(self, memberDict, num_actual_processes)
            continue

        res = re.search(r"\s*PMT host\s*:\s*(\S+)", line)
        if res:
            self.pmt_host = res.group(1)
            continue

        res = re.search(r"\s*PMT port\s*:\s*(\S+)", line)
        if res:
            self.pmt_port = res.group(1)
            continue

        res = re.search(r"\s*DAQ setup script\s*:\s*(\S+)",
                        line)
        if res:
            self.daq_setup_script = res.group(1)
            self.daq_dir = os.path.dirname( self.daq_setup_script ) + "/"
            continue

        res = re.search(r"\s*tcp_base_port\s*:\s*(\S+)",
                        line)
        if res:
            self.tcp_base_port = int( res.group(1) )
            continue

        res = re.search(r"\s*request_port\s*:\s*(\S+)",
                        line)
        if res:
            self.request_port = int( res.group(1) )
            continue

        res = re.search(r"\s*request_address\s*:\s*(\S+)",
                        line)
        if res:
            self.request_address = res.group(1)
            continue

        res = re.search(r"\s*partition_number\s*:\s*(\S+)",
                        line)
        if res:
            self.partition_number = int( res.group(1) )
            continue

        res = re.search(r"\s*debug level\s*:\s*(\S+)",
                        line)
        if res:
            self.debug_level = int(res.group(1))
            continue

        res = re.search(r"\s*manage processes\s*:\s*[tT]rue",
                        line)
        if res:
            self.manage_processes = True

        res = re.search(r"\s*manage processes\s*:\s*[fF]alse",
                        line)
        if res:
            self.manage_processes = False

        if "Subsystem" in line:

            res = re.search(r"\s*(\w+)\s+(\S+)\s*:\s*(\S+)", line)

            if not res:
                raise Exception("Exception in DAQInterface: "
                                "problem parsing " + daqinterface_config_filename +
                                " at line \"" + line + "\"")

            subsystemDict[res.group(2)] = res.group(3)

            filled = True
            
            for key, value in subsystemDict.items():
                if value is None:
                    filled = False

            if filled:
                self.subsystems.append(self.Subsystem(subsystemDict["id"],
                                                    subsystemDict["source"],
                                                    subsystemDict["destination"]))

                for varname in subsystemDict.keys():
                    subsystemDict[varname] = None

        if "EventBuilder" in line or \
                "DataLogger" in line or "Dispatcher" in line or \
                "RoutingMaster" in line:

            res = re.search(r"\s*(\w+)\s+(\S+)(?:\s*:\s*(\S+))?\s*$", line)

            if not res:
                raise Exception("Exception in DAQInterface: "
                                "problem parsing " + daqinterface_config_filename+
                                " at line \"" + line + "\"")

            memberDict["name"] = res.group(1)
            if res.group(3) != None:
                memberDict[res.group(2)] = res.group(3)
            else:
                raise Exception("Exception in DAQInterface: "
                                "problem parsing " + daqinterface_config_filename+
                                " at line \"" + line + "\"" + res.group(0))
            
            if res.group(2) == "host":
                num_expected_processes += 1


    if num_expected_processes != num_actual_processes:
        raise Exception(make_paragraph("An inconsistency exists in the boot file; a host was defined in the file for %d artdaq processes, but there's only a complete set of info in the file for %d processes. This may be the result of using a boot file designed for an artdaq version prior to the addition of a label requirement (see https://cdcvs.fnal.gov/redmine/projects/artdaq-utilities/wiki/The_boot_file_reference for more)" % (num_expected_processes, num_actual_processes)))

    return daqinterface_config_filename

def listdaqcomps_base(self):

    components_file = os.environ["DAQINTERFACE_KNOWN_BOARDREADERS_LIST"]

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

def listconfigs_base(self):
    subdirs = next(os.walk(get_config_parentdir()))[1]
    configs = [subdir for subdir in subdirs if subdir != "common_code" ]

    listconfigs_file="/tmp/listconfigs_" + os.environ["USER"] + ".txt"

    outf = open(listconfigs_file, "w")

    print
    print "Available configurations: "
    for config in sorted(configs):
        print config
        outf.write("%s\n" % config)

    print
    print "See file \"%s\" for saved record of the above configurations" % (listconfigs_file)
    print

def main():
    print "Calling listdaqcomps_base: "
    listdaqcomps_base("ignored_argument")

if __name__ == "__main__":
    main()
