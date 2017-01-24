
import re

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

