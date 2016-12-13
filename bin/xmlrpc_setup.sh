
# Get the products directory containing the xmlrpc_c package from the
# .settings file, and use it to set up an environment s.t. we have
# access to the xmlrpc executable

if [[ ! -e $PWD/.settings ]]; then
    echo "Unable to find .settings file in $PWD; this script should be executed from DAQInterface's base directory" >&2
    return 30
fi

proddir=$( cat $PWD/.settings | awk '/productsdir_for_xmlrpc/ { print $2 }' )

if [[ -n $proddir ]]; then

    . $proddir/setup 

    if [[ "$?" != "0" ]]; then
	echo "Attempted setup of $proddir failed; command will not work" >&2
	return 50
    fi
    
    num_xmlrpc_packages=$(ups list -aK+ xmlrpc_c | wc -l )

    if [[ "$num_xmlrpc_packages" == "0" ]]; then
	echo "Unable to find any xmlrpc_c packages in ${proddir}; command will not work" >&2
	return 60
    fi

    test "$num_xmlrpc_packages" -gt "1" && echo "Warning: found more than one possible xmlrpc_c package in ${proddir}; will pick one package at random for setup" >&2

    xmlrpc_setup_cmd=$( ups list -aK+ xmlrpc_c | tail -1 | awk '{print "setup xmlrpc_c",$2," -q ", $4}' )
    eval $xmlrpc_setup_cmd

    return 0
else
    echo "Unable to find valid products/ directory from .settings file" >&2
    return 40
fi
