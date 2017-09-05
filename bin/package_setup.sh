
# Get the products directory containing the desired package from the
# .settings file, and use it to perform a ups setup of the package

packagename=$1

if [[ -z $packagename ]]; then
    echo "An argument with the desired packagename is required" >&2
    return 70
fi

# 27-Jan-2017, KAB, if the requested package is already set up, let's assume that it's OK to use it
# (probably better tests that can be used...)
upcasePackageName=`echo ${packagename} | tr [a-z] [A-Z]`
prodDirEnvVar="${upcasePackageName}_DIR"
#echo $prodDirEnvVar
#echo ${!prodDirEnvVar}
if [[ -n "${!prodDirEnvVar}" ]]; then
    return
fi


if [[ ! -e $DAQINTERFACE_SETTINGS ]]; then
    echo "Unable to find DAQInterface settings file \"$DAQINTERFACE_SETTINGS\"" >&2
    return 30
fi

proddir=$( cat $DAQINTERFACE_SETTINGS | awk '/^[^#]*productsdir_for_bash_scripts/ { print $2 }' )
proddir=$( echo $( eval echo $proddir ) )  # Expand environ variables in string

if [[ -n $proddir ]]; then

    . $proddir/setup 

    if [[ "$?" != "0" ]]; then
	echo -e "\n\nCommand will not work: attempted setup of $proddir failed" >&2
	return 50
    fi
    
    num_packages=$(ups list -aK+ $packagename | wc -l )

    if [[ "$num_packages" == "0" ]]; then
	echo -e "\n\nCommand will not work: unable to find any $packagename packages in the following products path(s) in use: " >&2
	echo $PRODUCTS | tr ":" "\n" >&2
	echo
	return 60
    fi

    setup_cmd=$( ups list -aK+ $packagename | sort -n | tail -1 | awk '{print "setup $packagename",$2," -q ", $4}' )
    eval $setup_cmd

    return 0
else
    echo "Unable to find valid products/ directory from DAQInterface settings file \"$DAQINTERFACE_SETTINGS\"" >&2
    return 40
fi
