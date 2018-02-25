
import os
import sys
sys.path.append( os.environ["ARTDAQ_DAQINTERFACE_DIR"] )

import string
import re

from rc.control.utilities import table_range
from rc.control.utilities import commit_check_throws_if_failure

def bookkeeping_for_fhicl_documents_artdaq_v1_base(self):

    if os.path.exists(self.daq_dir + "/srcs/artdaq"):
        commit_check_throws_if_failure(self.daq_dir + "/srcs/artdaq", \
                                           "c3d1ce5ce07a83793f91efc0744b19aa8d5caf5c", "Jan 12, 2017", False)
    
    # JCF, 11/11/14

    # Now, set some variables which we'll use to replace
    # pre-existing variables in the FHiCL documents before we send
    # them to the artdaq processes

    # First passthrough of procinfos: assemble the
    # xmlrpc_client_list string, and figure out how many of each
    # type of process there are

    xmlrpc_client_list = "\""
    numeral = ""

    for procinfo in self.procinfos:
        if "BoardReader" in procinfo.name:
            numeral = "3"
        elif "EventBuilder" in procinfo.name:
            numeral = "4"
        elif "Aggregator" in procinfo.name:
            numeral = "5"

        xmlrpc_client_list += ";http://" + procinfo.host + ":" + \
            procinfo.port + "/RPC2," + numeral

    xmlrpc_client_list += "\""

    # Second passthrough: use this newfound info to modify the
    # FHiCL code we'll send during the config transition

    # Note that loops of the form "proc in self.procinfos" are
    # pass-by-value rather than pass-by-reference, so I need to
    # adopt a slightly cumbersome indexing notation

    for i_proc in range(len(self.procinfos)):

        self.procinfos[i_proc].fhicl_used = re.sub(
            "first_event_builder_rank.*\n",
            "first_event_builder_rank: " +
            str(self.num_boardreaders()) + "\n",
            self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub(
            "event_builder_count.*\n",
            "event_builder_count: " +
            str(self.num_eventbuilders()) + "\n",
            self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub(
            "xmlrpc_client_list.*\n",
            "xmlrpc_client_list: " +
            xmlrpc_client_list + "\n",
            self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub(
            "first_data_receiver_rank.*\n",
            "first_data_receiver_rank: " +
            str(self.num_boardreaders() +
                self.num_eventbuilders()) + "\n",
            self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub(
            "expected_fragments_per_event.*\n",
            "expected_fragments_per_event: " +
            str(self.num_boardreaders()) + "\n",
            self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub(
            "fragment_receiver_count.*\n",
            "fragment_receiver_count: " +
            str(self.num_boardreaders()) + "\n",
            self.procinfos[i_proc].fhicl_used)

        self.procinfos[i_proc].fhicl_used = re.sub(
            "data_receiver_count.*\n",
            "data_receiver_count: " +
            str(self.num_aggregators() - 1) + "\n",
            self.procinfos[i_proc].fhicl_used)



def bookkeeping_for_fhicl_documents_artdaq_v2_base(self):

    if os.path.exists(self.daq_dir + "/srcs/artdaq"):
        commit_check_throws_if_failure(self.daq_dir + "/srcs/artdaq", \
                                           "c3d1ce5ce07a83793f91efc0744b19aa8d5caf5c", "Jan 12, 2017", True)

        commit_check_throws_if_failure(self.daq_dir + "/srcs/artdaq", \
                                           "9a63dfd8660bfbba43acadcfa1ed4d362610be2f", "May 9, 2017", False)

    if self.num_aggregators() > 1:
        num_data_loggers = self.num_aggregators() - 1  # "-1" is for the dispatcher
    else:
        num_data_loggers = self.num_aggregators()

    assert num_data_loggers == 1, "Currently only have the logic to handle one data logger"

    max_fragment_size_words = self.max_fragment_size_bytes / 8

    proc_hosts = []

    for proctype in ["BoardReader", "EventBuilder", "Aggregator" ]:
        for procinfo in self.procinfos:
            if proctype in procinfo.name:
                num_existing = len(proc_hosts)

                if procinfo.host == "localhost":
                    host_to_display = os.environ["HOSTNAME"]
                else:
                    host_to_display = procinfo.host

                proc_hosts.append( 
                    "{rank: %d host: \"%s\" portOffset: %d}" % \
                        (num_existing, host_to_display, self.tcp_base_port + 10*num_existing))

    proc_hosts_string = ", ".join( proc_hosts )

    def create_sources_or_destinations_string(nodetype, first, last):

        if nodetype == "sources":
            prefix = "s"
        elif nodetype == "destinations":
            prefix = "d"
        else:
            assert False

        nodes = []

        for i in range(first, last):
            nodes.append( 
                "%s%d: { transferPluginType: Autodetect %s_rank: %d max_fragment_size_words: %d host_map: [%s]}" % \
                    (prefix, i, nodetype[:-1], i, max_fragment_size_words, \
                    proc_hosts_string))

        return "\n".join( nodes )

    source_node_first = -1
    source_node_last = -1
    destination_node_first = -1
    destination_node_last = -1
    
    agg_count = 0

    for i_proc in range(len(self.procinfos)):
        if "BoardReader" in self.procinfos[i_proc].name:
            destination_node_first = self.num_boardreaders()
            destination_node_last = self.num_boardreaders() + \
                self.num_eventbuilders()
            
        elif "EventBuilder" in self.procinfos[i_proc].name:
            source_node_first = 0
            source_node_last = self.num_boardreaders()
            destination_node_first = self.num_boardreaders() + \
                self.num_eventbuilders()
            destination_node_last = self.num_boardreaders() + \
                self.num_eventbuilders() + \
                num_data_loggers  

        elif "Aggregator" in self.procinfos[i_proc].name:
            source_node_first = self.num_boardreaders()
            source_node_last = self.num_boardreaders() + \
                self.num_eventbuilders()
        else:
            assert False

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

            if table_start != -1 and table_end != -1:
                self.procinfos[i_proc].fhicl_used = \
                    self.procinfos[i_proc].fhicl_used[:table_start] + \
                    "\n" + tablename + ": { \n" + \
                    create_sources_or_destinations_string(tablename, node_first, node_last) + \
                    "\n } \n" + \
                    self.procinfos[i_proc].fhicl_used[table_end:]
        
        if "Aggregator" in self.procinfos[i_proc].name:
            (table_start, table_end) = \
                table_range(self.procinfos[i_proc].fhicl_used, \
                                "transfer_to_dispatcher")
            if table_start == -1 or table_end == -1:
                raise Exception("Unable to find expected transfer_to_dispatcher transfer plugin definition in the Aggregator FHiCL")

            transfer_source_rank = self.num_boardreaders() + \
                self.num_eventbuilders() + \
                agg_count

            agg_count += 1

            transfer_destination_rank = self.num_boardreaders() + \
                self.num_eventbuilders() + num_data_loggers

            # JCF, Jan-24-2017
     
            # This is a kluge to account for the fact that the code can't
            # yet handle more than one data logger

            if transfer_source_rank == transfer_destination_rank:
                transfer_source_rank -= 1

            assert num_data_loggers < 2, "Code doesn't yet support multiple data loggers"

            transfer_code = self.procinfos[i_proc].fhicl_used[table_start:table_end]
            transfer_code = re.sub(r"source_rank\s*:\s*[0-9]+", 
                                   "source_rank: %d" % (transfer_source_rank),
                                   transfer_code)
            transfer_code = re.sub(r"destination_rank\s*:\s*[0-9]+",
                                   "destination_rank: %d" % (transfer_destination_rank),
                                   transfer_code)

            self.procinfos[i_proc].fhicl_used = \
                self.procinfos[i_proc].fhicl_used[:table_start] + \
                transfer_code + \
                self.procinfos[i_proc].fhicl_used[table_end:]

    for i_proc in range(len(self.procinfos)):
        self.procinfos[i_proc].fhicl_used = re.sub("expected_fragments_per_event\s*:\s*[0-9]+", 
                                                   "expected_fragments_per_event: %d" % (self.num_boardreaders()), 
                                                   self.procinfos[i_proc].fhicl_used)


# A lot of the code in this function repeats the code in
# bookkeeping_for_fhicl_documents_artdaq_v2_base. This is intentional
# - by not modularizing the repeated code, it means that it won't be
# possible to break backwards compatibility should we want to use
# artdaq v2_01_00 through artdaq v2_02_02 in the future

def bookkeeping_for_fhicl_documents_artdaq_v3_base(self):

    send_1_over_N = True

    try:
        if self.all_events_to_all_dispatchers:
            send_1_over_N = False
    except Exception:
        pass # We don't care if variable above is undefined

    max_fragment_size_words = self.max_fragment_size_bytes / 8

    if os.path.exists(self.daq_dir + "/srcs/artdaq"):
        commit_check_throws_if_failure(self.daq_dir + "/srcs/artdaq", \
                                           "68cb53e576dd6afea7950ca6286a08f5f329b966", "May 9, 2017", True)

    num_data_loggers = 0
    num_dispatchers = 0

    for procinfo in self.procinfos:
        if "DataLogger" in procinfo.name:
            num_data_loggers += 1
        elif "Dispatcher" in procinfo.name:
            num_dispatchers += 1

    proc_hosts = []

    for procinfo in self.procinfos:
        num_existing = len(proc_hosts)

        if procinfo.host == "localhost":
            host_to_display = os.environ["HOSTNAME"]
        else:
            host_to_display = procinfo.host

        proc_hosts.append( 
            "{rank: %d host: \"%s\" portOffset: %d}" % \
                (num_existing, host_to_display, self.tcp_base_port + 10*num_existing))

    proc_hosts_string = ", ".join( proc_hosts )

    def create_sources_or_destinations_string(nodetype, first, last, nth = -1, this_node_index = -1):

        if nodetype == "sources":
            prefix = "s"
        elif nodetype == "destinations":
            prefix = "d"
        else:
            assert False

        nodes = []

        for i in range(first, last):
            if nth == -1:
                nodes.append( 
                    "%s%d: { transferPluginType: Autodetect %s_rank: %d max_fragment_size_words: %d host_map: [%s]}" % \
                    (prefix, i, nodetype[:-1], i, max_fragment_size_words, \
                     proc_hosts_string))
            else:

                if nodetype == "destinations":
                    assert (last - first) == nth, "Problem with the NthEvent logic in the program: first node is %d, last is %d, but nth is %d" % (first, last, nth)

                    offset = (i - first) 
                elif nodetype == "sources":
                    offset = this_node_index

                nodes.append( 
                    "%s%d: { transferPluginType: NthEvent nth: %d offset: %d physical_transfer_plugin: { transferPluginType: Autodetect %s_rank: %d max_fragment_size_words: %d } host_map: [%s]}" % \
                    (prefix, i, nth, offset, nodetype[:-1], i, max_fragment_size_words, \
                     proc_hosts_string))

        return "\n".join( nodes )

    if send_1_over_N:
        current_dispatcher_index = 0

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
            destination_node_last = destination_node_first + num_data_loggers  

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

            source_node_first = self.num_boardreaders() + \
                                self.num_eventbuilders()
            source_node_last = source_node_first + num_data_loggers
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

            if table_start != -1 and table_end != -1:
                
                node_index = -1
                nth = -1

                if send_1_over_N:
                    if is_data_logger and tablename == "destinations":
                        nth = num_dispatchers
                    elif is_dispatcher and tablename == "sources":
                        nth = num_dispatchers
                        node_index = current_dispatcher_index
                        current_dispatcher_index += 1

                self.procinfos[i_proc].fhicl_used = \
                    self.procinfos[i_proc].fhicl_used[:table_start] + \
                    "\n" + tablename + ": { \n" + \
                    create_sources_or_destinations_string(tablename, node_first, node_last, nth, node_index) + \
                    "\n } \n" + \
                    self.procinfos[i_proc].fhicl_used[table_end:]

    expected_fragments_per_event = 0

    for procinfo in self.procinfos:

        if "BoardReader" in procinfo.name:

            res = re.search(r"[^#]\s*sends_no_fragments:\s*[Tt]rue", procinfo.fhicl_used)

            if not res:
                expected_fragments_per_event += 1
            else:
                continue                

    for i_proc in range(len(self.procinfos)):
        self.procinfos[i_proc].fhicl_used = re.sub("expected_fragments_per_event\s*:\s*[0-9]+", 
                                                   "expected_fragments_per_event: %d" % (expected_fragments_per_event), 
                                                   self.procinfos[i_proc].fhicl_used)


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
