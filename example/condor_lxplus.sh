#!/bin/bash
tar zxf venv.tar.gz >/dev/null 2>&1 # Supposedly this should succeed and should not cause errors
singularity exec -p -B ${PWD}:/srv --pwd /srv --nv \
   /cvmfs/unpacked.cern.ch/registry.hub.docker.com/fnallpc/fnallpc-docker:tensorflow-2.12.0-gpu-singularity \
   /bin/bash -c "source .env/bin/activate; python condor_lxplus_example.py ${0}"
