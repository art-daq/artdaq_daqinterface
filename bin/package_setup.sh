
# Get the products directory containing the desired package from the
# .settings file, and use it to perform a ups setup of the package

packagename=$1

if [[ -z $packagename ]]; then
    echo "An argument with the desired packagename is required" >&2
    return 70
fi


if [[ ! -e $PWD/.settings ]]; then
    echo "Unable to find .settings file in $PWD; this script should be executed from DAQInterface's base directory" >&2
    return 30
fi

proddir=$( cat $PWD/.settings | awk '/productsdir_for_bash_scripts/ { print $2 }' )

if [[ -n $proddir ]]; then

    . $proddir/setup 

    if [[ "$?" != "0" ]]; then
	echo "Attempted setup of $proddir failed; command will not work" >&2
	return 50
    fi
    
    num_packages=$(ups list -aK+ $packagename | wc -l )

    if [[ "$num_packages" == "0" ]]; then
	echo "Unable to find any $packagename packages in ${proddir}; command will not work" >&2
	return 60
    fi

    test "$num_packages" -gt "1" && echo "Warning: found more than one possible $packagename package in ${proddir}; will pick one package at random for setup" >&2

    setup_cmd=$( ups list -aK+ $packagename | tail -1 | awk '{print "setup $packagename",$2," -q ", $4}' )
    eval $setup_cmd

    return 0
else
    echo "Unable to find valid products/ directory from .settings file" >&2
    return 40
fi
