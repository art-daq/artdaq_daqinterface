#!/bin/env bash

full_cmd="xmlrpc http://localhost:5570/RPC2 state daqint "

( cd ~/artdaq-demo-base ; . setupARTDAQDEMO 2>&1 > /dev/null; echo $full_cmd ; eval $full_cmd )

