
BEGIN {
    
    in_artdaq_process_settings = 0
    in_subsystem_settings = 0

    # JCF, Sep-20-2019

    # Note that since request_address and table_update_address are
    # meant to have underscores even in the standard boot file
    # formate, and bookkeeping strips them of any surrounding quotes
    # they might have, that they don't need to be de-FHiCLized

    split("DAQ_setup_script debug_level PMT_host PMT_port disable_recovery manage_processes", vars_to_defhiclize, " ")
}

{

    if ( $0 ~ /^\s*$/ || $0 ~ /^\s*#.*/ ) {
	next
    }

    firstpart="not set"
    secondpart="not set"

    match($0, ":");

    if (RSTART != 0) {
	firstpart=substr($0, 1, RSTART-1);
	secondpart=substr($0, RSTART+1);
	# Handle lines with comments in them here?
	gsub(/^[ \t]+|[ \t]+$/, "", firstpart);
	gsub(/^[ \t]+|[ \t]+$/, "", secondpart);
    }


    if (firstpart == "artdaq_process_settings" ) {
	in_artdaq_process_settings = 1
	print "\n"
	next
    }

    if (in_artdaq_process_settings) {
	if ( $0 !~ /\}, \{/ && $0 !~ /\}\]/ ) {
	    gsub("\"", "", secondpart)
	    procinfo_vars[firstpart] = secondpart
	} else {
	
	    for (procinfo_var in procinfo_vars) {
		if (procinfo_var == "name") {
		    continue
		}

		if (procinfo_vars[ procinfo_var ] != "not set") {
		    printf("\n%s %s: %s", procinfo_vars["name"], procinfo_var, procinfo_vars[ procinfo_var ] )
		}
	    }

	    print "\n"
	    for (procinfo_var in procinfo_vars) {
		procinfo_vars[ procinfo_var ] = "not set"
	    } 

	    if ($0 ~ /\}\]/) {
		in_artdaq_process_settings = 0
	    }
	}
	next
    }


    if (firstpart == "subsystem_settings" ) {
	in_subsystem_settings = 1
	print "\n"
	next
    }

    if (in_subsystem_settings) {
	if ( $0 !~ /\}, \{/ && $0 !~ /\}\]/ ) {
	    gsub("\"", "", secondpart)
	    subsysteminfo_vars[firstpart] = secondpart
	} else {
	
	    for (subsysteminfo_var in subsysteminfo_vars) {
		if (subsysteminfo_vars[ subsysteminfo_var ] != "not set") {
		    printf("\nSubsystem %s: %s", subsysteminfo_var, subsysteminfo_vars[ subsysteminfo_var ] )
		}
	    }

	    print "\n"
	    for (subsysteminfo_var in subsysteminfo_vars) {
		subsysteminfo_vars[ subsysteminfo_var ] = "not set"
	    } 

	    if ($0 ~ /\}\]/) {
		in_subsystem_settings = 0
	    }
	}
	next
    }

    for ( var_index in vars_to_defhiclize ) {
	if (firstpart == vars_to_defhiclize[var_index]) {
	    gsub("_", " ", firstpart)
	    gsub("\"", "", secondpart)
	    printf("\n%s: %s", firstpart, secondpart);
	    next
	}
    }
}



