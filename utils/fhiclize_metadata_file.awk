#!/bin/env awk

# JCF, Oct-27-2016

# At Gennadiy's request, this script will convert the DAQInterface
# configuration file and metadata file into legal FHiCL code

{

    if (components_section_active) {
	if ( $0 !~ /Component #[0-9]/) {
	    printf "components: ["
	    for (i = 1; i <= length(components); ++i) {
		if (i != length(components)) {
		    printf "\"%s\", ", components[i]
		} else {
		    printf "\"%s\"]\n", components[i]
		}
	    }
	    components_section_active = 0
	}
    }

    if (boardreader_section_active) {
	if ( $0 !~ /^\s*$/) {
	    boardreaders[++boardreader_cntr] = $1
	    next
	} else {
	    printf "\nboardreader_logfiles: ["
	    for (i = 1; i <= length(boardreaders); ++i) {
		if (i != length(boardreaders)) {
		    printf "\"%s\", ", boardreaders[i]
		} else {
		    printf "\"%s\"]\n", boardreaders[i]
		}
	    }
	    boardreader_section_active = 0
	}
    }


    if (eventbuilder_section_active) {
	if ( $0 !~ /^\s*$/) {
	    eventbuilders[++eventbuilder_cntr] = $1
	    next
	} else {
	    printf "\neventbuilder_logfiles: ["
	    for (i = 1; i <= length(eventbuilders); ++i) {
		if (i != length(eventbuilders)) {
		    printf "\"%s\", ", eventbuilders[i]
		} else {
		    printf "\"%s\"]\n", eventbuilders[i]
		}
	    }
	    eventbuilder_section_active = 0
	}
    }

    if (aggregator_section_active) {
	if ( $0 !~ /^\s*$/) {
	    aggregators[++aggregator_cntr] = $1
	    next
	} else {
	    printf "\naggregator_logfiles: ["
	    for (i = 1; i <= length(aggregators); ++i) {
		if (i != length(aggregators)) {
		    printf "\"%s\", ", aggregators[i]
		} else {
		    printf "\"%s\"]\n\n", aggregators[i]
		}
	    }
	    aggregator_section_active = 0
	}
    }



    # Get the key / value pair; if there isn't one, then just continue

    colonloc=match($0, ":");

    if (RSTART != 0) { 
	firstpart=substr($0, 1, RSTART);
	secondpart=substr($0, RSTART+1);
	sub("^[ +]", "", secondpart)

	if (firstpart ~ "Config name" || firstpart ~ "Start time" ||
	    firstpart ~ "Stop time" || firstpart ~ "Total events" ) {
	    
	    firstpart = tolower(firstpart)
	    sub(" ", "_", firstpart)

	} else if (firstpart ~ /Component #[0-9]/) {
	    components[++component_cntr] = secondpart
	    components_section_active = 1
	    next
	} else if (firstpart ~ /^\/.*\/ commit/) {
	    next
	} else if (firstpart ~ "pmt logfile") {
	    printf "pmt_logfiles_wildcard: \"%s\"\n", secondpart
	    next
	} else if (firstpart ~ "boardreader logfiles") {
	    boardreader_section_active = 1
	    next
	} else if (firstpart ~ "eventbuilder logfiles") {
	    eventbuilder_section_active = 1
	    next
	} else if (firstpart ~ "aggregator logfiles") {
	    aggregator_section_active = 1
	    next
	} else {
	    gsub("[- ]+", "_", firstpart)
	}

	if (secondpart !~ /^[0-9.]+$/ ) {
	    print firstpart " \"" secondpart "\"";
	} else {
	    print firstpart " " secondpart
	}

    } else {
	#print $0;
	next
    }
}

# END {

#     # This section exists because the last line is an aggregator logfile line
#     printf "\naggregator_logfiles: ["
#     for (i = 1; i <= length(aggregators); ++i) {
# 	if (i != length(aggregators)) {
# 	    printf "\"%s\", ", aggregators[i]
# 	} else {
# 	    printf "\"%s\"]\n", aggregators[i]
# 	}
#     }
#     aggregator_section_active = 0
# }
