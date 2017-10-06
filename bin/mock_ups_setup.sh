
# JCF, Sep-6-2017

# This script, when sourced, is meant to simulate how the environment
# would change after DAQInterface was set up as a ups product

export DAQINTERFACE_DIR="directory_of_checked-out_DAQInterface_git_repository_needs_to_be_defined"

if ! [[ -e $DAQINTERFACE_DIR ]]; then

cat<<EOF

Error: directory "$DAQINTERFACE_DIR" referred to by the
DAQINTERFACE_DIR environment variable set in this script not only
isn't a DAQInterface installation, it doesn't even exist. Please edit
this script accordingly.

EOF

unset DAQINTERFACE_DIR
fi

export DAQINTERFACE_VERSION=1.0


export PATH=$DAQINTERFACE_DIR/bin:$PATH
