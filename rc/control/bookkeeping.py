
import os
import sys
sys.path.append( os.environ["ARTDAQ_DAQINTERFACE_DIR"] )

import string
import re

from rc.control.utilities import table_range
from rc.control.utilities import enclosing_table_range
from rc.control.utilities import enclosing_table_name
from rc.control.utilities import commit_check_throws_if_failure
from rc.control.utilities import make_paragraph
from rc.control.utilities import fhicl_writes_root_file

def bookkeeping_for_fhicl_documents_artdaq_v3_base(self):

    # Determine that the artdaq package used is new enough to be
    # compatible with the assumptions made by DAQInterface about the
    # interface artdaq offers

    # JCF, Nov-20-2018: update this when ready to require subsystem-compatible artdaq

    if os.path.exists(self.daq_dir + "/srcs/artdaq"):
        commit_check_throws_if_failure(self.daq_dir + "/srcs/artdaq", \
                                           "b434f3b71dd5c87da68d6b13f040701ff610fee1", "July 15, 2018", True)
    else:

        # JCF, Sep-20-2018: not yet logic for requiring an artdaq
        # version with a letter at the end of it (e.g., v3_02_01a as
        # opposed to v3_02_01)

        min_majorver = "3"
        min_minorver = "03"
        min_minorerver = "00"
        
        # ...so we'll also have a list of versions where if the artdaq
        # version matches one of them, we'll be considered OK

        other_allowed_versions = ["v3_02_01a"]

        version = self.get_package_version("artdaq")

        res = re.search(r"v([0-9])_([0-9]{2})_([0-9]{2})(.*)", version)
    
        if not res:
            raise Exception("Problem parsing the calculated version of artdaq, %s" % (version))

        majorver = res.group(1)
        minorver = res.group(2)
        minorerver = res.group(3)
        extension = res.group(4)

        passes_requirement = False

        if int(majorver) > int(min_majorver):
            passes_requirement = True
        elif int(majorver) == int(min_majorver):
            if int(minorver) > int(min_minorver):
                passes_requirement = True
            elif int(minorver) == int(min_minorver):
                if int(minorerver) >= int(min_minorerver):
                    passes_requirement = True

        if not passes_requirement:
            for an_allowed_version in other_allowed_versions:
                if version == an_allowed_version:
                    passes_requirement = True
                
        if not passes_requirement:
            raise Exception(make_paragraph("Version of artdaq set up by setup script \"%s\" is v%s_%s_%s%s; need a version at least as recent as v%s_%s_%s" % (self.daq_setup_script, majorver, minorver, minorerver, extension, min_majorver, min_minorver, min_minorerver)))

    for ss in self.subsystems:
        if self.subsystems[ss].destination != "not set":
            dest = self.subsystems[ss].destination
            if self.subsystems[dest] == None or (self.subsystems[dest].source != "not set" and self.subsystems[dest].source != ss):
                raise Exception(make_paragraph("Inconsistent subsystem configuration detected! Subsystem %d has destination %d, but subsystem %d has source %d!" % (ss, dest, dest, self.subsystems[dest].source)))
            self.subsystems[dest].source = ss

    # Start calculating values (fragment counts, memory sizes, etc.)
    # which will need to appear in the FHiCL

    # If advanced_memory_usage is set to true in the settings file,
    # read in the max fragment size meant to be provided by each
    # boardreader FHiCL

    if self.advanced_memory_usage:

        max_fragment_sizes = []

        for procinfo in self.procinfos:

            res = re.findall(r"\n[^#]*max_fragment_size_bytes\s*:\s*([0-9\.exabcdefABCDEF]+)", procinfo.fhicl_used)
            
            if "BoardReader" in procinfo.name:
                if len(res) > 0:
                    max_fragment_size_token = res[-1]

                    if max_fragment_size_token[0:2] != "0x":
                        max_fragment_size = int(float(max_fragment_size_token))
                    else:
                        max_fragment_size = int(max_fragment_size_token[2:], 16)

                    max_fragment_sizes.append( (procinfo.label, max_fragment_size) ) 
                else:
                    raise Exception(make_paragraph("Unable to find the max_fragment_size_bytes variable in the FHiCL document for %s; this is needed since \"advanced_memory_usage\" is set to true in the settings file, %s" % (procinfo.label, os.environ["DAQINTERFACE_SETTINGS"])))
            else:
                if len(res) > 0:
                    raise Exception(make_paragraph("max_fragment_size_bytes is found in the FHiCL document for %s; this parameter must not appear in FHiCL documents for non-BoardReader artdaq processes" % (procinfo.label)))

    # Now loop over the boardreaders again to determine
    # subsystem-level things, such as the number of fragments per
    # event produced by each subsystem's boardreader set, and the
    # amount of space those fragments take up

    fragments_per_boardreader = {}
    subsystem_fragment_count = { }
    subsystem_fragment_space = { }

    for procinfo in self.procinfos:
        if "BoardReader" in procinfo.name:

            generated_fragments_per_event = 1

            # JCF, Oct-12-2018: "sends_no_fragments: true" is
            # logically the same as "generated_fragments_per_event:
            # 0", but I'm keeping it for reasons of backwards
            # compatibility

            if re.search(r"\n\s*sends_no_fragments\s*:\s*[Tt]rue", procinfo.fhicl_used):
                generated_fragments_per_event = 0

            res = re.search(r"\n\s*generated_fragments_per_event\s*:\s*([0-9]+)", procinfo.fhicl_used)

            if res:
                generated_fragments_per_event = int(res.group(1))

            fragments_per_boardreader[ procinfo.label ] = generated_fragments_per_event
            subsystem_fragment_count[ procinfo.subsystem ] = subsystem_fragment_count.get(procinfo.subsystem, 0) + generated_fragments_per_event

            if self.advanced_memory_usage:
                list_of_one_fragment_size = [ proctuple[1] for proctuple in max_fragment_sizes if 
                                              proctuple[0] == procinfo.label ]
                assert len(list_of_one_fragment_size) == 1
                fragment_space = list_of_one_fragment_size[0]
            else:
                fragment_space = self.max_fragment_size_bytes
                
            subsystem_fragment_space[ procinfo.subsystem ] = subsystem_fragment_space.get(procinfo.subsystem, 0) + generated_fragments_per_event*fragment_space

    # Now using the per-subsystem info we've gathered, use recursion
    # to determine the *true* number of fragments per event and the
    # size they take up, since this quantity isn't just a function of
    # the boardreaders in the subystem but also of any connected
    # subsystems upstream whose eventbuilders send fragments down to
    # the subsystem in question

    def calculate_expected_fragments_per_event(ss, subsystem_fragment_count):
        count = subsystem_fragment_count.get(ss)

        if self.subsystems[ss].source != "not set":
            count += calculate_expected_fragments_per_event(self.subsystems[ss].source, subsystem_fragment_count)

        return count

    def calculate_max_event_size(ss, subsystem_fragment_space):
        size = subsystem_fragment_space.get(ss)

        if self.advanced_memory_usage:
            memory_scale_factor = 1.1
            size = int(float(size * memory_scale_factor))
            
            if size % 8 != 0:
                size += (8 - size % 8)
                assert size % 8 == 0, "Max event size not divisible by 8"

        if self.subsystems[ss].source != "not set":
            size += calculate_max_event_size(self.subsystems[ss].source, subsystem_fragment_space)

        return size

    expected_fragments_per_event = {}  
    for ss in self.subsystems:
        expected_fragments_per_event[ss] = calculate_expected_fragments_per_event(ss, subsystem_fragment_count)


    max_event_sizes = {}
    for ss in self.subsystems:
        max_event_sizes[ss] = calculate_max_event_size(ss, subsystem_fragment_space)

    # If we have advanced memory usage switched on, then make sure the
    # max_event_size_bytes gets set to the value calculated here in
    # bookkeeping, whether this involves adding the
    # max_event_size_bytes parameter or clobbering the existing one

    if self.advanced_memory_usage:
        for i_proc in range(len(self.procinfos)):
            if "BoardReader" not in self.procinfos[i_proc].name and "RoutingMaster" not in self.procinfos[i_proc].name:
                if re.search(r"\n[^#]*max_event_size_bytes\s*:\s*[0-9\.e]+", self.procinfos[i_proc].fhicl_used):
                    self.procinfos[i_proc].fhicl_used = re.sub("max_event_size_bytes\s*:\s*[0-9\.e]+",
                                                               "max_event_size_bytes: %d" % \
                                                               (max_event_sizes[self.procinfos[i_proc].subsystem]),
                                                               self.procinfos[i_proc].fhicl_used)
                else:

                    res = re.search(r"\n(\s*buffer_count\s*:\s*[0-9]+)", self.procinfos[i_proc].fhicl_used)

                    assert res, make_paragraph("artdaq's FHiCL requirements have changed since this code was written (DAQInterface expects a parameter called 'buffer_count' in %s, but this doesn't appear to exist -> DAQInterface code needs to be changed to accommodate this)" % (self.procinfos[i_proc].label))
                    
                    self.procinfos[i_proc].fhicl_used = re.sub(r"\n(\s*buffer_count\s*:\s*[0-9]+)",
                                                               "\n%s\nmax_event_size_bytes: %d" % (res.group(1), max_event_sizes[self.procinfos[i_proc].subsystem]),
                                                               self.procinfos[i_proc].fhicl_used)

    # Construct the host map string needed in the sources and destinations tables in artdaq process FHiCL

    proc_hosts = []

    for procinfo in self.procinfos:

        if procinfo.name == "RoutingMaster":
            continue
        
        if procinfo.host == "localhost":
            host_to_display = os.environ["HOSTNAME"]
        else:
            host_to_display = procinfo.host

        proc_hosts.append( 
            "{rank: %d host: \"%s\"}" % \
                (procinfo.rank, host_to_display))

    host_map_string = "host_map: [%s]" % (", ".join( proc_hosts ))

    # This function will construct the sources or destinations table
    # for a given process. If we're performing advanced memory usage,
    # the max event size will need to be provided; this value is used
    # to calculate the size of the buffers in the transfer plugins

    def create_sources_or_destinations_string(procinfo, nodetype, max_event_size, inter_subsystem_transfer = False):

        if nodetype == "sources":
            prefix = "s"
        elif nodetype == "destinations":
            prefix = "d"
        else:
            assert False, "nodetype passed to %s has to be either sources or destinations" % (create_sources_or_destinations_string.__name__)

        buffer_size_words = -1

        if self.advanced_memory_usage:

            if "BoardReader" in procinfo.name:

                list_of_one_fragment_size = [ proctuple[1] for proctuple in max_fragment_sizes if 
                                              proctuple[0] == procinfo.label ]
                assert len(list_of_one_fragment_size) == 1

                buffer_size_words = list_of_one_fragment_size[0] / 8

            elif "EventBuilder" not in procinfo.name or nodetype != "sources":
                buffer_size_words = max_event_size / 8
            else:
                pass  # For the EventBuilder, there's a different
                      # buffer size from each source, namely either
                      # the max fragment size coming from its
                      # corresponding BoardReader or, if the source is
                      # an EventBuilder from a parent subsystem, the
                      # relevant set of BoardReaders for the parent
                      # subsystem. We can't use just a single
                      # variable.

        else: # Not self.advanced_memory_usage
            if "BoardReader" in procinfo.name:
                buffer_size_words = self.max_fragment_size_bytes / 8
            elif "EventBuilder" not in procinfo.name or nodetype != "sources":
                res = re.search( r"\n\s*max_event_size_bytes\s*:\s*([0-9\.e]+)", procinfo.fhicl_used)
                if res:
                    max_event_size = int(float(res.group(1)))

                buffer_size_words = max_event_size / 8
            else:
                pass # Same comment for the advanced memory usage case above applies here

        procinfo_subystem_has_dataloggers = True
        if len([pi for pi in self.procinfos if pi.subsystem == procinfo.subsystem and pi.name == "DataLogger"]) == 0:
            procinfo_subsystem_has_dataloggers = False
                
        procinfos_for_string = []

        for procinfo_to_check in self.procinfos:
            add = False   # As in, "add this process we're checking to the sources or destinations table"

            if procinfo_to_check.subsystem == procinfo.subsystem and not inter_subsystem_transfer:
                if "BoardReader" in procinfo.name:
                    if "EventBuilder" in procinfo_to_check.name and nodetype == "destinations":
                        add = True
                elif "EventBuilder" in procinfo.name:
                    if "BoardReader" in procinfo_to_check.name and nodetype == "sources":
                        add = True
                    elif "DataLogger" in procinfo_to_check.name and nodetype == "destinations":
                        add = True
                    elif not procinfo_subsystem_has_dataloggers and "Dispatcher" in procinfo_to_check.name and nodetype == "destinations":
                        add = True
                elif "DataLogger" in procinfo.name:
                    if "EventBuilder" in procinfo_to_check.name and nodetype == "sources":
                        add = True
                    elif "Dispatcher" in procinfo_to_check.name and nodetype == "destinations":
                        add = True
                elif "Dispatcher" in procinfo.name:
                    if "DataLogger" in procinfo_to_check.name and nodetype == "sources":
                        add = True
                    elif not procinfo_subsystem_has_dataloggers and "EventBuilder" in procinfo_to_check.name and nodetype == "sources":
                        add = True
            if procinfo_to_check.subsystem != procinfo.subsystem and (inter_subsystem_transfer or nodetype == "sources"):   # the two processes are in separate subsystems
                if "EventBuilder" in procinfo.name and "EventBuilder" in procinfo_to_check.name:
                    if (nodetype == "destinations" and self.subsystems[procinfo.subsystem].destination == procinfo_to_check.subsystem) or \
                    (nodetype == "sources" and self.subsystems[procinfo_to_check.subsystem].destination == procinfo.subsystem):
                        add = True

            if add:
                procinfos_for_string.append( procinfo_to_check )

        nodes = []
                    
        for i_procinfo_for_string, procinfo_for_string in enumerate(procinfos_for_string):
            hms = host_map_string
            if i_procinfo_for_string != 0 and nodetype == "sources":
                hms = ""

            if nodetype == "sources" and "EventBuilder" in procinfo.name:
                if procinfo_for_string.name == "BoardReader":
                    if self.advanced_memory_usage:
                        list_of_one_fragment_size = [ proctuple[1] for proctuple in max_fragment_sizes if 
                                                      proctuple[0] == procinfo_for_string.label ]
                        assert len(list_of_one_fragment_size) == 1
                        buffer_size_words = list_of_one_fragment_size[0] / 8
                    else:
                        buffer_size_words = self.max_fragment_size_bytes / 8
                elif procinfo_for_string.name == "EventBuilder":
                    buffer_size_words = max_event_sizes[ procinfo_for_string.subsystem ] / 8
                else:
                    assert False, "A process type of %s shouldn't be considered for an EventBuilder's sources table" % (procinfo_for_string.name)
                
            assert buffer_size_words != -1
                
            nodes.append("%s%d: { transferPluginType: %s %s_rank: %d max_fragment_size_words: %d %s }" % \
                         (prefix, procinfo_for_string.rank, self.transfer, nodetype[:-1], procinfo_for_string.rank, \
                          buffer_size_words, hms) )

        return "\n".join( nodes )   # End function create_sources_or_destinations_string()

    for i_proc in range(len(self.procinfos)):

        for tablename in [ "sources", "destinations" ]:

            (table_start, table_end) =  table_range(self.procinfos[i_proc].fhicl_used, \
                                        tablename)

            inter_subsystem_transfer = False
            # TODO: Generate "binaryNetOutput" block if missing and needed!
            if enclosing_table_name(self.procinfos[i_proc].fhicl_used, tablename) == "binaryNetOutput":
                inter_subsystem_transfer = True

            # 13-Apr-2018, KAB: modified this statement from an "if" test to
            # a "while" loop so that it will modify all of the source and
            # destination blocks in a file. This was motivated by changes to
            # configuration files to move common parameter definitions into
            # included files, and the subsequent creation of multiple source
            # and destination blocks in PROLOGs.
            while table_start != -1 and table_end != -1:
                
                self.procinfos[i_proc].fhicl_used = \
                    self.procinfos[i_proc].fhicl_used[:table_start] + \
                    "\n" + tablename + ": { \n" + \
                    create_sources_or_destinations_string(self.procinfos[i_proc], tablename, max_event_sizes[ self.procinfos[i_proc].subsystem ], inter_subsystem_transfer) + \
                    "\n } \n" + \
                    self.procinfos[i_proc].fhicl_used[table_end:]

                searchstart = table_end
                (table_start, table_end) = \
                    table_range(self.procinfos[i_proc].fhicl_used, \
                                    tablename, searchstart)
                inter_subsystem_transfer = False
                if enclosing_table_name(self.procinfos[i_proc].fhicl_used, tablename, searchstart) == "binaryNetOutput":
                    inter_subsystem_transfer = True


    for i_proc in range(len(self.procinfos)):
        
        if "RoutingMaster" in self.procinfos[i_proc].name:

            nonsending_boardreaders = []
            for procinfo in self.procinfos:
                if "BoardReader" in procinfo.name:
                    if re.search(r"\n\s*sends_no_fragments\s*:\s*[Tt]rue", procinfo.fhicl_used) or \
                       re.search(r"\n\s*generated_fragments_per_event\s*:\s*0", procinfo.fhicl_used):
                        nonsending_boardreaders.append( procinfo.label )

            sender_ranks = "sender_ranks: [%s]" % ( ",".join( 
                [ str(otherproc.rank) for otherproc in self.procinfos if otherproc.subsystem == self.procinfos[i_proc].subsystem and "BoardReader" in otherproc.name and otherproc.label not in nonsending_boardreaders ] ))
            receiver_ranks = "receiver_ranks: [%s]" % ( ",".join( 
                [ str(otherproc.rank) for otherproc in self.procinfos if otherproc.subsystem == self.procinfos[i_proc].subsystem and "EventBuilder" in otherproc.name ] ))

            self.procinfos[i_proc].fhicl_used = re.sub("sender_ranks\s*:\s*\[.*\]",
                                                       sender_ranks,
                                                       self.procinfos[i_proc].fhicl_used)

            self.procinfos[i_proc].fhicl_used = re.sub("receiver_ranks\s*:\s*\[.*\]",
                                                       receiver_ranks,
                                                       self.procinfos[i_proc].fhicl_used)
     

    for i_proc in range(len(self.procinfos)):
        if "DataLogger" in self.procinfos[i_proc].name or "Dispatcher" in self.procinfos[i_proc].name:
            self.procinfos[i_proc].fhicl_used = re.sub("expected_fragments_per_event\s*:\s*[0-9]+", 
                                                       "expected_fragments_per_event: 1", 
                                                       self.procinfos[i_proc].fhicl_used)
        else:
            self.procinfos[i_proc].fhicl_used = re.sub("expected_fragments_per_event\s*:\s*[0-9]+", 
                                                       "expected_fragments_per_event: %d" % (expected_fragments_per_event[self.procinfos[i_proc].subsystem]), 
                                                       self.procinfos[i_proc].fhicl_used)
        if self.request_address is None:
            request_address = "227.128.%d.%d" % (self.partition_number, 128 + int(self.procinfos[i_proc].subsystem))
        else:
            request_address = self.request_address

        self.procinfos[i_proc].fhicl_used = re.sub("request_address\s*:\s*[\"0-9\.]+", 
                                                   "request_address: \"%s\"" % (request_address.strip("\"")), 
                                                   self.procinfos[i_proc].fhicl_used)

        if not self.request_port is None:
            self.procinfos[i_proc].fhicl_used = re.sub("request_port\s*:\s*[0-9]+", 
                                                       "request_port: %d" % (self.request_port), 
                                                       self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub("partition_number\s*:\s*[0-9]+", 
                                                   "partition_number: %d" % (self.partition_number), 
                                                   self.procinfos[i_proc].fhicl_used)

        if self.table_update_address is None:
            table_update_address = "227.129.%d.%d" % (self.partition_number, 128 + int(self.procinfos[i_proc].subsystem))
        else:
            table_update_address = self.table_update_address

        self.procinfos[i_proc].fhicl_used = re.sub("table_update_address\s*:\s*[\"0-9\.]+", 
                                                   "table_update_address: \"%s\"" % (table_update_address.strip("\"")), 
                                                   self.procinfos[i_proc].fhicl_used)
        
        if self.routing_base_port is None:
            routing_base_port = int(os.environ["ARTDAQ_BASE_PORT"]) + 10 + \
                                int(os.environ["ARTDAQ_PORTS_PER_PARTITION"])*self.partition_number + int(self.procinfos[i_proc].subsystem)
        else:
            routing_base_port = int(self.routing_base_port)

        self.procinfos[i_proc].fhicl_used = re.sub("routing_token_port\s*:\s*[0-9]+", 
                                                   "routing_token_port: %d" % (routing_base_port), 
                                                   self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub("table_update_port\s*:\s*[0-9]+", 
                                                   "table_update_port: %d" % (routing_base_port + 10), 
                                                   self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub("table_acknowledge_port\s*:\s*[0-9]+", 
                                                   "table_acknowledge_port: %d" % (routing_base_port + 20), 
                                                   self.procinfos[i_proc].fhicl_used)

        routingmaster_hostnames = [procinfo.host for procinfo in self.procinfos if procinfo.name == "RoutingMaster" and procinfo.subsystem == self.procinfos[i_proc].subsystem ]
        assert len(routingmaster_hostnames) == 0 or len(routingmaster_hostnames) == 1
    
        if len(routingmaster_hostnames) == 1:
            if routingmaster_hostnames[0] == "localhost":
                routingmaster_hostnames[0] = os.environ["HOSTNAME"]
            self.procinfos[i_proc].fhicl_used = re.sub("routing_master_hostname\s*:\s*\S+",
                                                       "routing_master_hostname: \"%s\"" % (routingmaster_hostnames[0].strip("\"")),
                                                       self.procinfos[i_proc].fhicl_used)


    if not self.data_directory_override is None:
        for i_proc in range(len(self.procinfos)):
            if "EventBuilder" in self.procinfos[i_proc].name or "DataLogger" in self.procinfos[i_proc].name:

                if fhicl_writes_root_file(self.procinfos[i_proc].fhicl_used):
                    # 17-Apr-2018, KAB: switched to using the "enclosing_table_range" function, rather
                    # than "table_range", since we want to capture all of the text inside the same
                    # block as the RootOutput FHiCL value.
                    # 30-Aug-2018, KAB: added support for RootDAQOutput
                    start, end = enclosing_table_range(self.procinfos[i_proc].fhicl_used, "RootOutput")
                    if start == -1 and end == -1:
                        start, end = enclosing_table_range(self.procinfos[i_proc].fhicl_used, "RootDAQOut")
                    assert start != -1 and end != -1

                    rootoutput_table = self.procinfos[i_proc].fhicl_used[start:end]

                    # 11-Apr-2018, KAB: changed the substition to only apply to the text
                    # in the rootoutput_table, and avoid picking up earlier fileName
                    # parameter strings in the document.
                    rootoutput_table = re.sub(r"(.*fileName\s*:[\s\"]*)/[^\s]+/",
                                              r"\1" + self.data_directory_override,
                                              rootoutput_table)

                    self.procinfos[i_proc].fhicl_used = self.procinfos[i_proc].fhicl_used[:start] + \
                                                        rootoutput_table + \
                                                        self.procinfos[i_proc].fhicl_used[end:]
                                                    
                

def bookkeeping_for_fhicl_documents_artdaq_v4_base(self):
    pass

def main():
    
    test_table_range = True

    if test_table_range:

        filename = "%s/simple_test_config/multiple_dispatchers/Aggregator2.fcl" % os.getcwd()

        inf = open( filename )
        
        inf_contents = inf.read()

        print "From file " + filename

        for tablename in ["sources", "destinations"]:
            (table_start, table_end) = table_range( inf_contents, tablename )
            
            print "Seven characters centered on table_start: \"" + inf_contents[(table_start - 3):(table_start+4)] + "\""
            print "Seven characters centered on table_end: \"" + inf_contents[(table_end - 3):(table_end+4)] + "\""
            print "The table_start: \"" + inf_contents[(table_start):(table_start+1)] + "\""
            print "The table_end: \"" + inf_contents[(table_end ):(table_end+1)] + "\""

if __name__ == "__main__":
    main()
