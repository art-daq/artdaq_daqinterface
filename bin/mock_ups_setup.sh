
# JCF, Sep-6-2017

# This script, when sourced, is meant to simulate how the environment
# would change after DAQInterface was set up as a ups product

export DAQINTERFACE_VERSION=1.0
export DAQINTERFACE_DIR="directory_of_checked-out_DAQInterface_git_repository_needs_to_be_defined"

export PATH=$DAQINTERFACE_DIR/bin:$PATH
