# HGCAL SiPM analysis using python

A Python-based package for processing HGCAL SiPM calibration data files for
detailed SiPM property analysis.

## Setup

The dependencies of this package require at least python3.8 to be set up. Here
we will be borrowing the `coffeateam/coffea` singularity image to set up this
environment, as it also includes many of the dependencies required by this
package, and is widely available in HEP clusters.

For the first time setup, you will want to run the following command:

```bash
mkdir workdir
cd workdir

wget https://raw.githubusercontent.com/UMDCMS/sipmanalyze/master/bootstrap.sh
chmod +x bootstrap.sh
./bootstrap.sh
```

For future usage, you can simply start the session using the newly generated script:

```bash
cd workdir
source ./start.sh
```

The first time you run this script, the package will automatically pull the
required packages. This will only be done for the first time setup, subsequent
`./start.sh` calls should be fast. If GPUs are available at the cluster in
question, the fitting package will automatically switch to using GPUs whenever
possible.

*Known issue*: because the `sipmpdf` fitting package requires the use of
`tensorflow` package, which in turns requires the use of CPUs with at least
Advanced Vector Extension 2 (AVX2). Certain clusters with very OLD CPU models
will not work.

## Running the code

Examples for running the code base is given as `jupyter` notebooks in the
`notebooks` directory. After starting up the session, you can host a `jupyter`
session simply as:

```bash
jupyter notebook --port 5125 # Or whatever port you are wish to use.
```

Then, interact with the notebook as usual. It would be encouraged that common
analysis routines be reorganized into python modules in the `src/sipmanalyze`
directory to allow for batch processing of data sets.


## Modifying or upgrading

After you have run set up process, the script will automatically clone the
latest git repositories of the `sipmpdf` and the `sipmanalyze`, after making the
edits (or updating the repository using `git pull` commands), run the following
commands in the singularity session for the edits to take effect:

## Note on the package split

The `sipmpdf` aims to be a standalone implementation of the SiPM response
functions using just the python numerical libraries, and is not limited to the
use case of the HGCAL calibration project. The `sipmanalyze` package is specific
to the data analysis designed for the HGCAL calibration project.
