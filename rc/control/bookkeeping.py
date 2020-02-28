
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
from rc.control.utilities import get_private_networks
from rc.control.utilities import zero_out_last_subnet

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

        self.fill_package_versions(["artdaq"])
        version = self.package_versions["artdaq"]

        res = re.search(r"v([0-9]+)_([0-9]+)_([0-9]+)(.*)", version)    

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

            if "max_event_size_bytes" in procinfo.fhicl_used:
                raise Exception(make_paragraph("max_event_size_bytes is found in the FHiCL document for %s; this parameter must not appear in FHiCL documents when \"advanced_memory_usage\" is set to true in the settings file %s. This is because DAQInterface calculates and then adds this parameter during bookkeeping." %  (procinfo.label, os.environ["DAQINTERFACE_SETTINGS"])))

    # Now loop over the boardreaders again to determine
    # subsystem-level things, such as the number of fragments per
    # event produced by each subsystem's boardreader set, and the
    # amount of space those fragments take up

    fragments_per_boardreader = {}
    subsystem_fragment_count = { }
    subsystem_fragment_space = { }

    for ss in self.subsystems:
        subsystem_fragment_count[ss] = 0
        subsystem_fragment_space[ss] = 0

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
            subsystem_fragment_count[ procinfo.subsystem ] += generated_fragments_per_event

            if self.advanced_memory_usage:
                list_of_one_fragment_size = [ proctuple[1] for proctuple in max_fragment_sizes if 
                                              proctuple[0] == procinfo.label ]
                assert len(list_of_one_fragment_size) == 1
                fragment_space = list_of_one_fragment_size[0]
            else:
                fragment_space = self.max_fragment_size_bytes
                
            subsystem_fragment_space[ procinfo.subsystem ] += generated_fragments_per_event*fragment_space

    # Now using the per-subsystem info we've gathered, use recursion
    # to determine the *true* number of fragments per event and the
    # size they take up, since this quantity isn't just a function of
    # the boardreaders in the subystem but also of any connected
    # subsystems upstream whose eventbuilders send fragments down to
    # the subsystem in question

    def calculate_expected_fragments_per_event(ss):
        count = subsystem_fragment_count[ss]

        for ss_source in self.subsystems[ss].sources:
            if self.subsystems[ss].fragmentMode:
                count += calculate_expected_fragments_per_event(ss_source)
            else:
                count += 1

        return count

    def calculate_max_event_size(ss):
        size = subsystem_fragment_space[ss]

        if self.advanced_memory_usage:
            memory_scale_factor = 1.1
            size = int(float(size * memory_scale_factor))
            
            if size % 8 != 0:
                size += (8 - size % 8)
                assert size % 8 == 0, "Max event size not divisible by 8"

        for ss_source in self.subsystems[ss].sources:
            size += calculate_max_event_size(ss_source)

        return size

    expected_fragments_per_event = {}  
    for ss in self.subsystems:
        expected_fragments_per_event[ss] = calculate_expected_fragments_per_event(ss)


    max_event_sizes = {}
    for ss in self.subsystems:
        max_event_sizes[ss] = calculate_max_event_size(ss)

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

    procinfos_sorted_by_rank = sorted(self.procinfos, key=lambda procinfo: procinfo.rank)
    for procinfo in procinfos_sorted_by_rank:

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

        procinfo_subsystem_has_dataloggers = True
        if len([pi for pi in self.procinfos if pi.subsystem == procinfo.subsystem and pi.name == "DataLogger"]) == 0:
            procinfo_subsystem_has_dataloggers = False
                
        procinfos_for_string = []

        for procinfo_to_check in procinfos_sorted_by_rank:
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
            if i_procinfo_for_string != 0 and (nodetype == "sources" or nodetype == "destinations"):
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

    def get_router_process_identifier(procinfo):
        if "RoutingMaster" in procinfo.name:
            return "RoutingMaster"
        elif "DFO" in procinfo.label:
            return "DFO"
        else:
            return None

    router_process_info = {}
    router_process_info["RoutingMaster"] = { "location" : "child_subsystem" }
    router_process_info["DFO"] = { "location" : "parent_subsystem" }

    # Couple of sanity checks

    for procinfo in self.procinfos:
        
        # A DFO shouldn't share a subsystem with any other eventbuilders 

        if get_router_process_identifier(procinfo) == "DFO":
            rogue_eventbuilders = [ pi.label for pi in self.procinfos if "EventBuilder" in pi.name and pi.subsystem == procinfo.subsystem and pi.label != procinfo.label ]
            if len(rogue_eventbuilders) > 0:
                raise Exception(make_paragraph("The following EventBuilder(s) were found in subsystem %s, location of DFO process %s; a DFO can't share a subsystems with other EventBuilders: %s" % (procinfo.subsystem, procinfo.label, " ".join(rogue_eventbuilders))))

        # There shouldn't be a RoutingMaster in a subsystem with a parent subsystem which contains a DFO

        if get_router_process_identifier(procinfo) == "DFO":
            rogue_routingmasters = [pi.label for pi in self.procinfos if "RoutingMaster" in pi.name and self.subsystems[procinfo.subsystem].destination == pi.subsystem]
            if len(rogue_routingmasters) > 0:
                raise Exception(make_paragraph("A RoutingMaster was found in subsystem %s; this is illegal since a parent of subsystem %s, subsystem %s, contains a DFO (%s). The problem RoutingMaster(s): %s" % (self.subsystems[procinfo.subsystem].destination, self.subsystems[procinfo.subsystem].destination, procinfo.subsystem, procinfo.label, " ".join(rogue_routingmasters))))

    for i_proc in range(len(self.procinfos)):

        for tablename in [ "sources", "destinations" ]:

            (table_start, table_end) =  table_range(self.procinfos[i_proc].fhicl_used, \
                                        tablename)

            def determine_if_inter_subsystem_transfer(procinfo, table_name, table_searchstart):
                for enclosing_sender_table in ["routingNetOutput", "binaryNetOutput"]:
                    if enclosing_table_name(procinfo.fhicl_used, table_name, table_searchstart) == enclosing_sender_table:
                        return True

                return False

            searchstart = 0
            inter_subsystem_transfer = determine_if_inter_subsystem_transfer(self.procinfos[i_proc], tablename, searchstart)

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

                inter_subsystem_transfer = determine_if_inter_subsystem_transfer(self.procinfos[i_proc], tablename, searchstart)


    for i_proc in range(len(self.procinfos)):

        router_process_identifier = get_router_process_identifier(self.procinfos[i_proc])

        if router_process_identifier is not None:

            nonsending_boardreaders = []
            for procinfo in self.procinfos:
                if "BoardReader" in procinfo.name:
                    if re.search(r"\n\s*sends_no_fragments\s*:\s*[Tt]rue", procinfo.fhicl_used) or \
                       re.search(r"\n\s*generated_fragments_per_event\s*:\s*0", procinfo.fhicl_used):
                        nonsending_boardreaders.append( procinfo.label )

            # The routingmaster in subsystem N should consider as senders both boardreaders in subsystem N 
            # and eventbuilders in subsystem M if subsystem M is a parent of subsystem N

            boardreaders_in_sender_ranks = [ int(otherproc.rank) for otherproc in procinfos_sorted_by_rank if otherproc.subsystem == self.procinfos[i_proc].subsystem and "BoardReader" in otherproc.name and otherproc.label not in nonsending_boardreaders ]

            eventbuilders_in_sender_ranks = [ int(otherproc.rank) for otherproc in procinfos_sorted_by_rank if "EventBuilder" in otherproc.name and self.subsystems[otherproc.subsystem].destination == self.procinfos[i_proc].subsystem ]

            sorted_sender_ranks_list = sorted(boardreaders_in_sender_ranks + eventbuilders_in_sender_ranks, key=lambda rank: rank)

            router_location = router_process_info[ router_process_identifier ]["location"]
            if router_location == "child_subsystem":
                sorted_receiver_ranks_list = [ str(otherproc.rank) for otherproc in procinfos_sorted_by_rank if otherproc.subsystem == self.procinfos[i_proc].subsystem and "EventBuilder" in otherproc.name ]
            elif router_location == "parent_subsystem":
                sorted_receiver_ranks_list = [ str(otherproc.rank) for otherproc in procinfos_sorted_by_rank if otherproc.subsystem == self.subsystems[self.procinfos[i_proc].subsystem].destination and "EventBuilder" in otherproc.name ]
            else:
                assert False, "Developer error: logic needs to be added here for the %s case of a router process location" % (router_location)

            sender_ranks = "sender_ranks: [%s]" % ( ",".join( [str(rnk) for rnk in sorted_sender_ranks_list] ))
            receiver_ranks = "receiver_ranks: [%s]" % ( ",".join( sorted_receiver_ranks_list ))

            self.procinfos[i_proc].fhicl_used = re.sub("sender_ranks\s*:\s*\[[^\]]*\]",
                                                       sender_ranks,
                                                       self.procinfos[i_proc].fhicl_used, 0, re.DOTALL)

            self.procinfos[i_proc].fhicl_used = re.sub("receiver_ranks\s*:\s*\[[^\]]*\]",
                                                       receiver_ranks,
                                                       self.procinfos[i_proc].fhicl_used, 0, re.DOTALL)
     

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

        self.procinfos[i_proc].fhicl_used = re.sub("partition_number\s*:\s*[0-9]+", 
                                                   "partition_number: %d" % (self.partition_number), 
                                                   self.procinfos[i_proc].fhicl_used)

    # JCF, Apr-17-2019

    # For this next pass over the artdaq processes, we'll bookkeep the
    # parameters (ports, addresses, etc.) describing the physical
    # hookup of the routingmaster to its connected processes. So,
    # let's memo-ize these parameters

    # JCF, Jun-19-2019

    # Note the convention here: a router process (currently just a
    # RoutingMaster or a DFO) is associated with the subsystem it's in
    # charge of sending stuff to - so while a RoutingMaster is
    # actually in the subsystem it's associated with, a DFO is in the
    # parent subsystem of the subsystem it's associated with. Here
    # "associated with" translates to "what subsystem do we use when
    # bookkeeping")

    # JCF, Aug-15-2019

    # First, let's figure out which private networks the various
    # processes can see, assuming the user hasn't disabled private
    # network bookkeeping. Note to developers: if, for whatever
    # reason, you decide it's a good idea to fill the
    # private_networks_seen dictionary even if the disabling's
    # occured, you'll want to revisit the logic later in this function
    # that assumes nonempty private_networks_seen dictionary <=> the
    # user wants private network bookkeeping

    private_networks_seen = {}
    if not self.disable_private_network_bookkeeping:
        for host in set([procinfo.host for procinfo in self.procinfos]):
            private_networks = get_private_networks(host)
            for procinfo in self.procinfos:
                if procinfo.host == host:
                    private_networks_seen[procinfo.label] = private_networks

    assert not self.disable_private_network_bookkeeping or len(private_networks_seen) == 0, \
        "See Aug-15-2019 comment in bookkeeping.py"

    table_update_addresses = {}
    routing_base_ports = {}
    router_process_hostnames = {}
    router_process_private_networks = {}

    for subsystem_id, subsystem in self.subsystems.items():

        router_process_for_subsystem_as_list = []
        
        for procinfo in self.procinfos:
            router_process_identifier = get_router_process_identifier(procinfo)
            if router_process_identifier is None:
                continue
            
            if router_process_info[ router_process_identifier ]["location"] == "child_subsystem" and procinfo.subsystem == subsystem_id:
                router_process_for_subsystem_as_list.append( procinfo )
            elif router_process_info[ router_process_identifier ]["location"] == "parent_subsystem" and procinfo.subsystem in self.subsystems[subsystem_id].sources:
                router_process_for_subsystem_as_list.append( procinfo )

        if len(router_process_for_subsystem_as_list) == 0:
            continue
        elif len(router_process_for_subsystem_as_list) > 1:
            raise Exception(make_paragraph("DAQInterface has found more than one router process (RoutingMaster, DFO, etc.) associated with subsystem %s requested in the boot file %s; this isn't currently supported" % (subsystem_id, self.boot_filename)))
        elif len(router_process_for_subsystem_as_list) == 1:
            router_process_for_subsystem = router_process_for_subsystem_as_list[0]
            
            table_update_addresses[ subsystem_id ] = "227.129.%d.%d" % (self.partition_number, \
                                                                        int(subsystem_id) + 128)
            routing_base_ports[ subsystem_id ] = int(os.environ["ARTDAQ_BASE_PORT"]) + 10 + \
                                                 int(os.environ["ARTDAQ_PORTS_PER_PARTITION"])*self.partition_number + int(subsystem_id)

            router_process_hostnames[ subsystem_id ] = router_process_for_subsystem.host
            if router_process_hostnames[ subsystem_id ] == "localhost":
                router_process_hostnames[ subsystem_id ] = os.environ["HOSTNAME"]

            if not self.disable_private_network_bookkeeping:

                # To-do: Tiebreaker needed in case the process group can see more than one private network...
                router_process_private_networks[ subsystem_id ] = None

                relevant_processes = []
                for procinfo in self.procinfos:
                    if "BoardReader" in procinfo.name and procinfo.subsystem == subsystem_id and \
                       procinfo.label not in nonsending_boardreaders:
                        relevant_processes.append(procinfo.label)
                    elif "EventBuilder" in procinfo.name and self.subsystems[procinfo.subsystem].destination == subsystem_id and not get_router_process_identifier(procinfo) == "DFO":
                        relevant_processes.append(procinfo.label)
                       

                for router_process_private_network_candidate in private_networks_seen[router_process_for_subsystem.label]:
                    network_seen_by_relevant_processes = True

                    for relevant_process in relevant_processes:
                        if zero_out_last_subnet(router_process_private_network_candidate) not in \
                           [zero_out_last_subnet(ntwrk) for ntwrk in private_networks_seen[relevant_process]]:
                                network_seen_by_relevant_processes = False

                    if network_seen_by_relevant_processes:
                        router_process_private_networks[ subsystem_id ] = router_process_private_network_candidate
                        break

                if router_process_private_networks[ subsystem_id ] is None:
                    self.print_log("w", make_paragraph("Warning: disable_private_network_bookkeeping isn't set to true in the DAQInterface settings file \"%s\" -- it defaults to false if unset -- but no private network was found visible both to the routing process %s and the all the processes the routing process works with (%s)" % \
                                                       (os.environ["DAQINTERFACE_SETTINGS"], router_process_for_subsystem.label, ", ".join(relevant_processes))))
        
        # While we're looping on subsystems, let's also bookkeep the
        # multicast_interface_ip parameter used for request sending, by 
        # figuring out whether or not all the request-receiving boardreaders 
        # and eventbuilders in the subsystem see the same private network

        if not self.disable_private_network_bookkeeping:
            boardreaders_involved_in_requests = []
            eventbuilders_involved_in_requests = []

            for procinfo in [procinfo for procinfo in self.procinfos if procinfo.subsystem == subsystem_id]:
                if "BoardReader" in procinfo.name and procinfo.label not in nonsending_boardreaders:
                    for token in ["[Ww]indow", "[Ss]ingle", "[Bb]uffer"]:
                        res = re.search(r"\n\s*request_mode\s*:\s*\"?%s\"?" % (token), procinfo.fhicl_used)
                        if res:
                            boardreaders_involved_in_requests.append(procinfo.label)
                            break

                if "EventBuilder" in procinfo.name:
                    res = re.search(r"\n\s*send_requests\s*:\s*true", procinfo.fhicl_used)
                    if res:
                        eventbuilders_involved_in_requests.append(procinfo.label)

            processes_involved_in_requests = [process for process_list in \
                                              [boardreaders_involved_in_requests, eventbuilders_involved_in_requests] \
                                              for process in process_list ]

            if len(processes_involved_in_requests) > 0:
                private_networks_seen_by_processes_involved_in_requests = set( [zero_out_last_subnet(ntwrk) for ntwrk in private_networks_seen[processes_involved_in_requests[0]]] )
                for i_proc in range(1, len(processes_involved_in_requests)):
                    private_networks_seen_by_processes_involved_in_requests = private_networks_seen_by_processes_involved_in_requests.intersection(set( [zero_out_last_subnet(ntwrk) for ntwrk in private_networks_seen[processes_involved_in_requests[i_proc]]] ))

                # JCF, Aug-12-2019
                # Don't yet have a "tiebreaker" if there's more than one private network visible to all processes...

                if len(list(private_networks_seen_by_processes_involved_in_requests)) > 0:
                    multicast_interface_ip = list(private_networks_seen_by_processes_involved_in_requests)[0]
                    for process_involved_in_request in processes_involved_in_requests:
                        for i_proc in range(len(self.procinfos)):
                            if self.procinfos[i_proc].label == process_involved_in_request:
                                self.procinfos[i_proc].fhicl_used = re.sub("multicast_interface_ip\s*:\s*\S+", \
                                                                           "multicast_interface_ip: \"%s\"" % \
                                                                           (multicast_interface_ip), \
                                                                           self.procinfos[i_proc].fhicl_used)
                else:
                    self.print_log("w", make_paragraph("Warning: disable_private_network_bookkeeping isn't set to true in the DAQInterface settings file \"%s\" -- it defaults to false if unset -- but no private network was found visible to all the processes involved in data requests for subsystem %s: %s" % (os.environ["DAQINTERFACE_SETTINGS"], str(subsystem_id), ", ".join(processes_involved_in_requests) )))

    # JCF, Apr-18-2019

    # bookkeep_table_for_routing_master takes any parameters in a
    # table related to a routing_master, and bookkeeps them so they
    # refer to the routing_master in routing_master_subsystem

    # JCF, Jun-19-2019

    # Rename the function bookkeep_table_for_router_process, and have
    # it cover both routing_masters (RoutingMasters) and DFOs

    def bookkeep_table_for_router_process(i_proc, router_process_subsystem, tablename):

        table_start, table_end = table_range(self.procinfos[i_proc].fhicl_used, tablename)

        if table_start != -1:
            should_be_negative_one, dummy = table_range(self.procinfos[i_proc].fhicl_used[table_end:], tablename)
            if should_be_negative_one != -1:
                raise Exception(make_paragraph("The table \"%s\" appears more than once in the FHiCL config for process \"%s\"; this is not allowed" % (tablename, self.procinfos[i_proc].label)))
            
        #if table_start == -1 or table_end == -1:
        #    raise Exception(make_paragraph("router process for subsystem %s requires that a FHiCL table called \"%s\" exists in process %s's FHiCL, but none was found" % (router_process_subsystem, tablename, self.procinfos[i_proc].label)))

        table_to_bookkeep = self.procinfos[i_proc].fhicl_used[table_start:table_end]

        table_to_bookkeep = re.sub("table_update_address\s*:\s*[\"0-9\.]+", 
                                      "table_update_address: \"%s\"" % (table_update_addresses[router_process_subsystem].strip("\"")),
                                      table_to_bookkeep)
        table_to_bookkeep = re.sub("table_update_port\s*:\s*[0-9]+", 
                                      "table_update_port: %d" % (routing_base_ports[router_process_subsystem] + 10), 
                                      table_to_bookkeep)
        table_to_bookkeep = re.sub("table_acknowledge_port\s*:\s*[0-9]+", 
                                      "table_acknowledge_port: %d" % (routing_base_ports[router_process_subsystem] + 20), 
                                      table_to_bookkeep)
        table_to_bookkeep = re.sub("routing_token_port\s*:\s*[0-9]+", 
                                      "routing_token_port: %d" % (routing_base_ports[router_process_subsystem]), 
                                      table_to_bookkeep)

        if "RoutingMaster" not in self.procinfos[i_proc].name or not self.disable_private_network_bookkeeping:
            table_to_bookkeep = re.sub("routing_master_hostname\s*:\s*\S+",
                                       "routing_master_hostname: \"%s\"" % (router_process_hostnames[router_process_subsystem].strip("\"")),
                                       table_to_bookkeep)

        # So far in this function we've just set
        # routing_master_hostname to the router process hostname from
        # the boot file and left table_update_multicast_interface
        # untouched, but let's see if we can use a shared private
        # network...

        if not self.disable_private_network_bookkeeping and router_process_private_networks[router_process_subsystem] is not None:
            for private_network_seen in private_networks_seen[self.procinfos[i_proc].label]:

                if zero_out_last_subnet(private_network_seen) == zero_out_last_subnet(router_process_private_networks[router_process_subsystem]):

                    routing_master_hostname_value = router_process_private_networks[router_process_subsystem]
                    table_update_multicast_interface_value = zero_out_last_subnet(private_network_seen)

                    table_to_bookkeep = re.sub("routing_master_hostname\s*:\s*\S+",
                                               "routing_master_hostname: \"%s\"" % (routing_master_hostname_value),
                                               table_to_bookkeep)

                    table_to_bookkeep = re.sub("table_update_multicast_interface\s*:\s*\S+",
                                               "table_update_multicast_interface: \"%s\"" % (table_update_multicast_interface_value),
                                               table_to_bookkeep)
                    break

        self.procinfos[i_proc].fhicl_used = self.procinfos[i_proc].fhicl_used[:table_start] + \
                            "\n" + table_to_bookkeep + "\n" + \
                            self.procinfos[i_proc].fhicl_used[table_end:]


    for i_proc in range(len(self.procinfos)):

        if get_router_process_identifier(self.procinfos[i_proc]) == "RoutingMaster":
            bookkeep_table_for_router_process(i_proc, self.procinfos[i_proc].subsystem, "daq")
        elif get_router_process_identifier(self.procinfos[i_proc]) == "DFO":
            bookkeep_table_for_router_process(i_proc, self.subsystems[self.procinfos[i_proc].subsystem].destination, "art")
        elif "BoardReader" in self.procinfos[i_proc].name:
            br_subsystem = self.procinfos[i_proc].subsystem
            router_process_subsystem = br_subsystem

            if router_process_subsystem not in router_process_hostnames: 
                continue

            if not re.search(r"\n\s*sends_no_fragments\s*:\s*[Tt]rue", self.procinfos[i_proc].fhicl_used) and \
               not re.search(r"\n\s*generated_fragments_per_event\s*:\s*0", self.procinfos[i_proc].fhicl_used):                
                bookkeep_table_for_router_process(i_proc, router_process_subsystem, "routing_table_config")
         
        elif "EventBuilder" in self.procinfos[i_proc].name:
            eb_subsystem = self.procinfos[i_proc].subsystem

            if eb_subsystem in router_process_hostnames: 
                bookkeep_table_for_router_process(i_proc, eb_subsystem, "routing_token_config")

            unflattened_parents_of_subsystems_with_routing_masters = [self.subsystems[subsystem_id].sources for subsystem_id in self.subsystems if subsystem_id in [rm.subsystem for rm in self.procinfos if get_router_process_identifier(rm) == "RoutingMaster"] ]
            parents_of_subsystems_with_routing_masters = [subsystem_id for parents in unflattened_parents_of_subsystems_with_routing_masters for subsystem_id in parents]

            if eb_subsystem in parents_of_subsystems_with_routing_masters:
                bookkeep_table_for_router_process(i_proc, self.subsystems[eb_subsystem].destination, "routing_table_config")

    firstLoggerRank = 9999999

    for procinfo in self.procinfos:
        if fhicl_writes_root_file(procinfo.fhicl_used):
            if procinfo.rank < firstLoggerRank:
                firstLoggerRank = procinfo.rank

    for i_proc in range(len(self.procinfos)):
        if fhicl_writes_root_file(self.procinfos[i_proc].fhicl_used):
            res = re.search(r"firstLoggerRank\s*:\s*\S+", self.procinfos[i_proc].fhicl_used)
            if res:
                self.procinfos[i_proc].fhicl_used = re.sub("firstLoggerRank\s*:\s*\S+", "firstLoggerRank: %d" % (firstLoggerRank), self.procinfos[i_proc].fhicl_used)

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
                                                    
    for fhicl_key, fhicl_value in self.bootfile_fhicl_overwrites.iteritems():
        print fhicl_key, fhicl_value
        for i_proc in range(len(self.procinfos)):
            self.procinfos[i_proc].fhicl_used = re.sub(r"%s\s*:\s*\S+" % (fhicl_key), \
                                                       "%s: %s" % (fhicl_key, fhicl_value), \
                                                       self.procinfos[i_proc].fhicl_used)
        
                                                                         

def bookkeeping_for_fhicl_documents_artdaq_v4_base(self):
    pass

