
# Need to supply "desired_run"

BEGIN {
    in_run=0
    last_filename=""
}

/Started run/ {

# Assume an output form along the lines of "Started run 7563"
    
    start1=match($0, "Started run")
    
    split(substr($0, start1), array)

    run = array[3]

    if (run == desired_run) {
	print FILENAME
	in_run=1
    } else {
	in_run=0
    }
}


{
#    print FILENAME

    if (in_run==1 && last_filename != FILENAME) {
	print FILENAME
    } 

    last_filename = FILENAME
}
