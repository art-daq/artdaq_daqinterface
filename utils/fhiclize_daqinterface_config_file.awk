#!/bin/env awk

# JCF, Oct-27-2016

# At Gennadiy's request, this script will convert the DAQInterface
# configuration file and metadata file into legal FHiCL code

function print_fhicl_sequence(KEY, SEQ, i_s) {
    printf "%s: [", KEY
    for (i_s = 1; i_s <= length(SEQ); ++i_s) {
	if (i_s != length(SEQ)) {
	    printf "\"%s\", ", SEQ[i_s]
	} else {
	    printf "\"%s\"]\n", SEQ[i_s]
	}
    }
}

{
    # Get the key / value pair; if there isn't one, then just continue

    colonloc=match($0, ":");

    if (RSTART != 0) { 
	firstpart=substr($0, 1, RSTART);
	secondpart=substr($0, RSTART+1);
	sub("^[ +]", "", secondpart)

	if (firstpart ~ "EventBuilder host") {
	    eventbuilder_hosts[++eventbuilder_host_cntr] = secondpart
	    next
	} else if (firstpart ~ "EventBuilder port") {
	    eventbuilder_ports[++eventbuilder_port_cntr] = secondpart
	    next
	} else if (firstpart ~ "Aggregator host") {
	    aggregator_hosts[++aggregator_host_cntr] = secondpart
	    next
	} else if (firstpart ~ "Aggregator port") {
	    aggregator_ports[++aggregator_port_cntr] = secondpart
	    next
	} else if (firstpart ~ "max file size") {

	    print_fhicl_sequence("Eventbuilder_hosts", eventbuilder_hosts)	    
	    print_fhicl_sequence("Eventbuilder_ports", eventbuilder_ports)

	    print_fhicl_sequence("Aggegator_hosts", aggregator_hosts)
	    print_fhicl_sequence("Aggregator_ports", aggregator_ports)

	    print "max_file_size: " secondpart
	    next
	} else if (firstpart ~ "max file time") {
	    print "max_file_time: " secondpart
	    next
	} else {
	    gsub("[- ]+", "_", firstpart)
	}

	if (secondpart !~ /^[0-9.]+$/ ) {
	    print firstpart " \"" secondpart "\"";
	} else {
	    print firstpart " " secondpart
	}
    }
}
