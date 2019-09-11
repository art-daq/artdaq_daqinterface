#!/bin/env awk


{
    match($0, "^\\s*#")  # Skip commented lines
    if (RSTART != 0) {
       next
    }

    # Get the key / value pair; if there isn't one, then just continue

    match($0, ":");

    if (RSTART == 0) {
	next
    } else { 
	firstpart=substr($0, 1, RSTART-1);
	secondpart=substr($0, RSTART+1);

	sub("^\\s*","", firstpart);
	sub("\\s*$","", firstpart);
	gsub("\\s+", "_", firstpart);

	sub("^\\s*","", secondpart);
	sub("\\s*$","", secondpart);


	process_names["BoardReader"] = "now defined"
	process_names["EventBuilder"] = "now defined"
	process_names["DataLogger"] = "now defined"
	process_names["Dispatcher"] = "now defined"
	process_names["RoutingMaster"] = "now defined"

	process_tokens["host"] = "now defined"
	process_tokens["port"] = "now defined"
	process_tokens["label"] = "now defined"
	process_tokens["subsystem"] = "now defined"

	for (process_name in process_names) {
	    for (process_token in process_tokens) {
		keymatch = sprintf("%s_%s", process_name, process_token)

		if (firstpart ~ keymatch) {
		    if (process_token != "port") {
			lists[ firstpart ] = sprintf("%s \"%s\",", lists[firstpart], secondpart);
		    } else {
			lists[ firstpart ] = sprintf("%s %s,", lists[firstpart], secondpart);
		    }

		    next
		}
	    }
	}

	if ((secondpart !~ /^[0-9.]+$/ || gsub("\\.", ".", secondpart) > 1) && (secondpart !~ /^\".*\"$/) && (secondpart !~ /^\[.*\]$/)) {
	    print firstpart ": \"" secondpart "\"";
	} else {
	    print firstpart ": " secondpart
	}
    }
}

END {

    for (list in lists) {
	sub("^\\s+", "", lists[list])
	sub("\\s+$", "", lists[list])
	sub(",$","", lists[list])
	printf("\n%ss: [%s]", list, lists[list])
    }
}
