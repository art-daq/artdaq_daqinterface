#!/bin/env bash

. $DAQINTERFACE_DIR/bin/daqinterface_functions.sh

if (($num_daqinterfaces > 0 )); then
    list_daqinterfaces
else
    echo "No instances of DAQInterface are up"
fi

