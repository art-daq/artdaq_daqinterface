
import os
import sys
sys.path.append( os.environ["ARTDAQ_DAQINTERFACE_DIR"] )

import string
import re

from rc.control.utilities import table_range
from rc.control.utilities import enclosing_table_range
from rc.control.utilities import commit_check_throws_if_failure
from rc.control.utilities import make_paragraph
from rc.control.utilities import fhicl_writes_root_file

def bookkeeping_for_fhicl_documents_artdaq_v3_base(self):

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

    max_event_size = 0

    if self.advanced_memory_usage:

        memory_scale_factor = 1.1
        max_fragment_sizes = []

        for procinfo in self.procinfos:

            res = re.findall(r"\n[^#]*max_fragment_size_bytes\s*:\s*([0-9\.e]+)", procinfo.fhicl_used)
            
            if "BoardReader" in procinfo.name:
                if len(res) > 0:
                    max_fragment_size = int(float(res[-1]))
                    max_event_size += max_fragment_size

                    max_fragment_sizes.append( (procinfo.label, max_fragment_size) ) 
                else:
                    raise Exception(make_paragraph("Unable to find the max_fragment_size_bytes variable in the FHiCL document for %s; this is needed since \"advanced_memory_usage\" is set to true in the settings file, %s" % (procinfo.label, os.environ["DAQINTERFACE_SETTINGS"])))
            else:
                if len(res) > 0:
                    raise Exception(make_paragraph("max_fragment_size_bytes is found in the FHiCL document for %s; this parameter must not appear in FHiCL documents for non-BoardReader artdaq processes" % (procinfo.label)))

        max_event_size = int(float(max_event_size * memory_scale_factor))

        if max_event_size % 8 != 0:
            max_event_size += (8 - max_event_size % 8)

        assert max_event_size % 8 == 0, "Max event size not divisible by 8"
        
        for i_proc in range(len(self.procinfos)):
            if "BoardReader" not in self.procinfos[i_proc].name and "RoutingMaster" not in self.procinfos[i_proc].name:
                if re.search(r"\n[^#]*max_event_size_bytes\s*:\s*[0-9\.e]+", self.procinfos[i_proc].fhicl_used):
                    self.procinfos[i_proc].fhicl_used = re.sub("max_event_size_bytes\s*:\s*[0-9\.e]+",
                                                               "max_event_size_bytes: %d" % (max_event_size),
                                                               self.procinfos[i_proc].fhicl_used)
                else:

                    res = re.search(r"\n(\s*buffer_count\s*:\s*[0-9]+)", self.procinfos[i_proc].fhicl_used)

                    assert res, make_paragraph("artdaq's FHiCL requirements have changed since this code was written (DAQInterface expects a parameter called 'buffer_count' in %s, but this doesn't appear to exist -> DAQInterface code needs to be changed to accommodate this)" % (self.procinfos[i_proc].label))
                    
                    self.procinfos[i_proc].fhicl_used = re.sub(r"\n(\s*buffer_count\s*:\s*[0-9]+)",
                                                               "\n%s\nmax_event_size_bytes: %d" % (res.group(1), max_event_size),
                                                               self.procinfos[i_proc].fhicl_used)

    num_data_loggers = 0
    num_dispatchers = 0

    for procinfo in self.procinfos:
        if "DataLogger" in procinfo.name:
            num_data_loggers += 1
        elif "Dispatcher" in procinfo.name:
            num_dispatchers += 1

    proc_hosts = []

    for procinfo in self.procinfos:
        if procinfo.name == "RoutingMaster":
            continue
        
        num_existing = len(proc_hosts)

        if procinfo.host == "localhost":
            host_to_display = os.environ["HOSTNAME"]
        else:
            host_to_display = procinfo.host

        proc_hosts.append( 
            "{rank: %d host: \"%s\"}" % \
                (num_existing, host_to_display))

    proc_hosts_string = ", ".join( proc_hosts )

    def create_sources_or_destinations_string(i_proc, nodetype, first, last, max_event_size = -1):

        if nodetype == "sources":
            prefix = "s"
        elif nodetype == "destinations":
            prefix = "d"
        else:
            assert False

        nodes = []

        for i in range(first, last):
            if i == first or nodetype == "destinations":
                host_map_string = "host_map: [%s]" % (proc_hosts_string)
            else:
                host_map_string = ""

            if self.advanced_memory_usage:

                if "BoardReader" in self.procinfos[i_proc].name:

                    list_of_one_fragment_size = [ proctuple[1] for proctuple in max_fragment_sizes if 
                                                  proctuple[0] == self.procinfos[i_proc].label ]
                    assert len(list_of_one_fragment_size) == 1

                    max_fragment_size = list_of_one_fragment_size[0]

                    nodes.append( 
                        "%s%d: { transferPluginType: %s %s_rank: %d max_fragment_size_words: %d %s }" % \
                        (prefix, i, self.transfer, nodetype[:-1], i, max_fragment_size / 8, \
                         host_map_string))
                elif "EventBuilder" in self.procinfos[i_proc].name and nodetype == "sources":
                    nodes.append( 
                        "%s%d: { transferPluginType: %s %s_rank: %d max_fragment_size_words: %d %s }" % \
                        (prefix, i, self.transfer, nodetype[:-1], i, max_fragment_sizes[i][1] / 8, \
                         host_map_string))

                else:
                    nodes.append( 
                        "%s%d: { transferPluginType: %s %s_rank: %d max_fragment_size_words: %d %s }" % \
                        (prefix, i, self.transfer, nodetype[:-1], i, max_event_size / 8, \
                         host_map_string))
            else:  # Not self.advanced_memory_usage

                max_fragment_size_words = self.max_fragment_size_bytes / 8
                res = re.search( r"\n\s*max_event_size_bytes\s*:\s*([0-9\.e]+)", self.procinfos[i_proc].fhicl_used)
                if res:
                    max_event_size = int(float(res.group(1)))

                else:
                    max_event_size = self.max_fragment_size_bytes * self.num_boardreaders()

                if "BoardReader" in self.procinfos[i_proc].name or \
                   ("EventBuilder" in self.procinfos[i_proc].name and nodetype == "sources"):
                    nodes.append( 
                        "%s%d: { transferPluginType: %s %s_rank: %d max_fragment_size_words: %d %s }" % \
                        (prefix, i, self.transfer, nodetype[:-1], i, max_fragment_size_words, \
                         host_map_string))
                else:
                    nodes.append( 
                        "%s%d: { transferPluginType: %s %s_rank: %d max_fragment_size_words: %d %s }" % \
                        (prefix, i, self.transfer, nodetype[:-1], i, max_event_size / 8, \
                         host_map_string))

        return "\n".join( nodes )

    for i_proc in range(len(self.procinfos)):

        source_node_first = -1
        source_node_last = -1
        destination_node_first = -1
        destination_node_last = -1

        is_data_logger = False
        is_dispatcher = False

        if "BoardReader" in self.procinfos[i_proc].name:
            destination_node_first = self.num_boardreaders()
            destination_node_last = destination_node_first + \
                                    self.num_eventbuilders()
            
        elif "EventBuilder" in self.procinfos[i_proc].name:
            source_node_first = 0
            source_node_last = source_node_first + self.num_boardreaders()
            destination_node_first = self.num_boardreaders() + \
                self.num_eventbuilders()
            if num_data_loggers > 0:
                destination_node_last = destination_node_first + num_data_loggers  
            else:
                destination_node_last = destination_node_first + num_dispatchers

        elif "DataLogger" in self.procinfos[i_proc].name:
            is_data_logger = True

            source_node_first = self.num_boardreaders()
            source_node_last = self.num_boardreaders() + \
                               self.num_eventbuilders()

            destination_node_first = self.num_boardreaders() + \
                                     self.num_eventbuilders() + \
                                     num_data_loggers
            destination_node_last =  self.num_boardreaders() + \
                                     self.num_eventbuilders() + \
                                     num_data_loggers + \
                                     num_dispatchers
        elif "Dispatcher" in self.procinfos[i_proc].name:
            is_dispatcher = True

            if num_data_loggers > 0:
                source_node_first = self.num_boardreaders() + \
                                    self.num_eventbuilders()
                source_node_last = source_node_first + num_data_loggers
            else:
                source_node_first = self.num_boardreaders()
                source_node_last = source_node_first + self.num_eventbuilders()

        elif "RoutingMaster" in self.procinfos[i_proc].name:
            pass
        else:
            assert False, "Process type not recognized"

        for tablename in [ "sources", "destinations" ]:

            if tablename == "sources":
                node_first = source_node_first
                node_last = source_node_last
            else:
                node_first = destination_node_first
                node_last = destination_node_last

 
            (table_start, table_end) = \
                table_range(self.procinfos[i_proc].fhicl_used, \
                                tablename)

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
                    create_sources_or_destinations_string(i_proc, tablename, node_first, node_last, max_event_size) + \
                    "\n } \n" + \
                    self.procinfos[i_proc].fhicl_used[table_end:]

                (table_start, table_end) = \
                    table_range(self.procinfos[i_proc].fhicl_used, \
                                    tablename, table_end)

    expected_fragments_per_event = 0

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

            expected_fragments_per_event += generated_fragments_per_event

    for procinfo in self.procinfos:
        
        if "RoutingMaster" in procinfo.name:

            sender_ranks = "sender_ranks: [%s]" % ( ",".join( 
                [ str(rank) for rank in range(0,self.num_boardreaders()) ] ))
            receiver_ranks = "receiver_ranks: [%s]" % ( ",".join( 
                [ str(rank) for rank in range(self.num_boardreaders(), 
                                              self.num_boardreaders() + self.num_eventbuilders()) ] ))

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
                                                       "expected_fragments_per_event: %d" % (expected_fragments_per_event), 
                                                       self.procinfos[i_proc].fhicl_used)
        if self.request_address is None:
            self.request_address = "227.128.%d.129" % (self.partition_number)

        self.procinfos[i_proc].fhicl_used = re.sub("request_address\s*:\s*[\"0-9\.]+", 
                                                   "request_address: \"%s\"" % (self.request_address.strip("\"")), 
                                                   self.procinfos[i_proc].fhicl_used)

        if not self.request_port is None:
            self.procinfos[i_proc].fhicl_used = re.sub("request_port\s*:\s*[0-9]+", 
                                                       "request_port: %d" % (self.request_port), 
                                                       self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub("partition_number\s*:\s*[0-9]+", 
                                                   "partition_number: %d" % (self.partition_number), 
                                                   self.procinfos[i_proc].fhicl_used)

        if self.table_update_address is None:
            self.table_update_address = "227.129.%d.129" % (self.partition_number)

        self.procinfos[i_proc].fhicl_used = re.sub("table_update_address\s*:\s*[\"0-9\.]+", 
                                                   "table_update_address: \"%s\"" % (self.table_update_address.strip("\"")), 
                                                   self.procinfos[i_proc].fhicl_used)
        
        if self.routing_base_port is None:
            self.routing_base_port = int(os.environ["ARTDAQ_BASE_PORT"]) + 10 + \
                                     int(os.environ["ARTDAQ_PORTS_PER_PARTITION"])*self.partition_number

        self.procinfos[i_proc].fhicl_used = re.sub("routing_token_port\s*:\s*[0-9]+", 
                                                   "routing_token_port: %d" % (int(self.routing_base_port)), 
                                                   self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub("table_update_port\s*:\s*[0-9]+", 
                                                   "table_update_port: %d" % (int(self.routing_base_port) + 10), 
                                                   self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub("table_acknowledge_port\s*:\s*[0-9]+", 
                                                   "table_acknowledge_port: %d" % (int(self.routing_base_port) + 20), 
                                                   self.procinfos[i_proc].fhicl_used)

        routingmaster_hostnames = [procinfo.host for procinfo in self.procinfos if procinfo.name == "RoutingMaster"]
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
