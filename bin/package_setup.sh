
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

proddir=$( sed -r -n 's/^\s*productsdir[_ ]for[_ ]bash[_ ]scripts\s*:\s*(\S+).*/\1/p' $DAQINTERFACE_SETTINGS )
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

    unsetup_all()
    {
	for pp in `printenv | sed -ne '/^SETUP_/{s/SETUP_//;s/=.*//;p}'`;do
            test $pp = UPS && continue;
            prod=`echo $pp | tr 'A-Z' 'a-z'`;
            eval "tmp=\${SETUP_$pp-}";
            test -z "$tmp" && echo already unsetup && continue;
            unsetup -j $prod;
	done
    }

    # Call Ron's unsetup function. Remove the ups packages of the
    # environment which sourced package_setup to avoid unnecessary version
    # conflicts. Note that this also requires that package_setup not have
    # already been sourced in the environment; if it HAS, then unsetup_all
    # will remove a package which the externval environment needs

    if [[ -z $DAQINTERFACE_ALREADY_CALLED_PACKAGE_SETUP ]]; then
	export DAQINTERFACE_ALREADY_CALLED_PACKAGE_SETUP=true
	unsetup_all
    else
	cat >&2 <<EOF

        DEVELOPER ERROR: package_setup.sh shouldn't be sourced twice
        in the same environment as its first action is to unsetup any
        previously-set-up ups package. Please contact John Freeman at
        jcfree@fnal.gov. 

EOF
	return 1
    fi

    setup_cmd=$( ups list -aK+ $packagename | sort -n | tail -1 | awk '{print "setup $packagename",$2," -q ", $4}' )
    eval $setup_cmd

    return 0
else
    echo "Unable to find valid products/ directory from DAQInterface settings file \"$DAQINTERFACE_SETTINGS\"" >&2
    return 40
fi
