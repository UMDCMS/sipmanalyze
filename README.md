# HGCAL SiPM analysis using python

A python-based package for processing HGCAL SiPM calibration data files for
detailed SiPM property analysis.

## Setup

The dependecies of this package requires python3.8 to be set up. Here we will be
borrowing the `coffeateam/coffea` singularity image to set up this environment,
as it also includes many of the depedencies required by this package, and is
widely available in HEP clusters.

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
./start.sh
```

## Modifying or upgrading

After you have run set up process, the script will automatically clone the
latest git repositories of the `sipmpdf` and the `sipmanalyze`, after making the
edits (or updating the repository using `git pull` commands), run the following
commands in the singularity session for the edits to take effect:

```bash
python -m pip install ./sipmpdf
python -m pip install ./sipmanalyze
```

## Note on the package split

The `sipmpdf` aims to be a standalone implementation of the SiPM response
functions using just the python numerical libraries, and is not limited to the
use case of the HGCAL calibration project. The `sipmanalyze` package is specific
to the data analysis designed for the HGCAL calibration project at UMD.
