
BEGIN {
    
    in_artdaq_process_settings = 0
    in_subsystem_settings = 0
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

		printf("\n%s %s: %s", procinfo_vars["name"], procinfo_var, procinfo_vars[ procinfo_var ] )
	    }

	    print "\n"
	    for (procinfo_var in procinfo_vars) {
		procinfo_vars[ procinfo_var ] = "not set"
	    } 
	}
    }
}



