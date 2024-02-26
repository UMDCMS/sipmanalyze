# Running analysis using condor

If you want to run the analysis routine using condor, the way you need to go
about doing this will vary by machine, due to the technologies available at
each machine.

## Fermilab LPC

For interacting with condor or batch processes, the simplest method would be to
use `dask` to call function directly in your interactive process. We have
provided a simple class for handling how the various methods are transmitted in
the using the `sipmanalyze.condor.make_lpc_client` method. A simple script one
can run would be:


## CERN lxplus

As of writing, the equivalent of `lpcjobqueue` on lxplus,
[`dask-lxplus`][dask-lxplus], does not support the spawning job queues in from
singularity images. For this we will need to run condor jobs in a more
old-fashioned way. The following instructions assume that you have created the
environment following default bootstrap instructions. Examples of the files
show below can be found in the [`examples/condor_lxplus*`](../examples) files. 

- Step 1. Prepare a tarball of the execution environment (notice that working
  path is important, as tarball works with relative directory in mind)
  ```bash
  cd workdir # Or "cd /srv" if you are running this command within singularity
  tar --exclude-caches-all zcf venv.tar.gz .env sipmanalyze sipmpdf
  ```
- Step 2: Prepare your python script. Notice that the python script can at most
  have 1 command line input that is modified by the condor job index (This is a
  hard limit of how condor handle command line arguments in general scripts).

- Step 3: Prepare the bash script. The bash script will need to first extract
  the tar ball, then load in the singularity session used for the base
  environment, then load in the customized environment, then run the python
  script of interest. A minimum working examples would be something like:
  ```bash
  #!/bin/bash
  tar zxf venv.tar.gz >/dev/null 2>&1 # Supposedly this should succeed and should not cause errors
  singularity exec -p -B ${PWD}:/srv --pwd /srv --nv \
   /cvmfs/unpacked.cern.ch/registry.hub.docker.com/fnallpc/fnallpc-docker:tensorflow-2.12.0-gpu-singularity \
   /bin/bash -c "source .env/bin/activate; python condor_lxplus_example.py ${0}"
  ```

- Step 4: Prepare the condor JDL configurations. Here one will need to specify
  transferring the tarball and the python script to the remote worker:
  ```
  executable           = condor_lxplus.sh
  requirements         = (OpSysAndVer =?= "CentOS7")
  +JobFlavour          = "longlunch"
  Transfer_Input_Files = venv.tar.gz, condor_lxplus_example.py
  inputs               = $(ProcId)
  output               = sipm_analyze_lxplus_example.$(ClusterId).$(ProcId).stdout
  error                = sipm_analyze_lxplus_example.$(ClusterId).$(ProcId).stderr
  log                  = sipm_analyze_lxplus_example.$(ClusterId).$(ProcId).log
  queue 10
  ```

With this, you can then submit the JDL file of interest.

Notice that this method requires a lot more file-keeping on the side of the
analyzer, and thus is much less desirable than the solution that is available
with working with condor directly using `dask`.


[dask-lxplus]: https://github.com/cernops/dask-lxplus
