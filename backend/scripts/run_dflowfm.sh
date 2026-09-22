#!/bin/bash
# Wrapper script for Delft3D D-Flow FM execution
# Ensures correct Intel Fortran runtime library (libifport.so.5) is available in LD_LIBRARY_PATH

export LD_LIBRARY_PATH=/opt/intel/oneapi/2026.1/lib:$LD_LIBRARY_PATH

# Pass all arguments to the actual executable
/home/agent001/Downloads/Delft3D/build_dflowfm_release/install/bin/dflowfm "$@"
