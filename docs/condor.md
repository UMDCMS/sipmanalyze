# Running analysis using condor

If you want to run the analysis routine using condor, the way you need to go
about doing this will vary by machine, due to the technologies available at
each machine.

## Using `dask`

For interacting with condor or batch processes, the simplest method would be to
use `dask` to call function directly in your interactive process.

This method is currently under construction, and will not work with either
[`lpcjobqueue`][lpcjobqueue] or [`dask-lxplus`][dask-lxplus].


## Vanilla condor script usage

As of writing, both `lpcjobqueue` and `dask-lxplus` has issues spawning
compatible jobs due to the heavy dependency of `zfit` and `tensorflow`. The
following instructions are done for running condor jobs right now the
old-fashioned way. The instructions assume that you have created the
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

[lpcjobqueue]: https://github.com/CoffeaTeam/lpcjobqueue
[dask-lxplus]: https://github.com/cernops/dask-lxplus
