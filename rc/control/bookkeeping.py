
import string
import re
import os

from rc.control.utilities import table_range


def bookkeeping_for_fhicl_documents_artdaq_v2_base(self):

    # JCF, Jan-24-2017
    # Will need to think about how to handle max_fragment_size_words...
    max_fragment_size_words = 2097152

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
                        (num_existing, host_to_display, 6300 + 10*num_existing))

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
                "%s%d: { transferPluginType: MPI %s_rank: %d max_fragment_size_words: %d host_map: [%s]}" % \
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
                self.num_aggregators() - 1  # "-1" is for the dispatcher

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
                self.num_eventbuilders() + \
                self.num_aggregators() - 1

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


def bookkeeping_for_fhicl_documents_artdaq_v1_base(self):
    
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

