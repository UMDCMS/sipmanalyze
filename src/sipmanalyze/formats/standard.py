"""

waveform.py

Handling waveform-like data inputs

The file will handled the data formats that is used for the SiPM calibration
analysis. All data formats is expected to be handled using awkward arrays, which
gives us the most coverage with ROOT files used by HEP, and the python numerical
analysis tools like numpy and scipy. This also allows for flexible and arbitrary
data formats to be loaded in without the need for a predefined structure. The
return of these `from_` functions will typically be either awkward arrays.

"""
from typing import Dict, Union, List
from dataclasses import dataclass

import textwrap
import awkward
import uproot
import numpy


@dataclass
class standard_runinfo:
  test: int
  pass


@dataclass
class standard_container:
  runinfo: standard_runinfo
  data: awkward.Array

  @staticmethod
  def from_txt(filename):
    arr = numpy.genfromtxt(filename, dtype=numpy.float32)
    if arr.shape[1] == 5:
      # Old style format with only 5 columns and readout data
      blank = awkward.zeros_like(arr[:, 0])
      data = awkward.zip({
        'time': blank,
        'det_id': blank,
        'gantry_x': arr[:, 0],
        'gantry_y': arr[:, 1],
        'gantry_z': arr[:, 2],
        'led_bv': blank,
        'led_temp': blank,
        'sipm_temp': blank,
      })
      data['payload'] = awkward.from_regular(arr[:, 3:])
    elif arr.shape[1] >= 9:  # Old format with mulitple columns
      data = awkward.zip({
        'time': arr[:, 0],
        'det_id': arr[:, 1],
        'gantry_x': arr[:, 2],
        'gantry_y': arr[:, 3],
        'gantry_z': arr[:, 4],
        'led_bv': arr[:, 5],
        'led_temp': arr[:, 6],
        'sipm_temp': arr[:, 7],
        # Naming the data "payload", translations will need to be handled by the
        # user, since the columns are not labelled.
      })
      data['payload'] = awkward.from_regular(arr[:, 8:])
    else:
      raise RuntimeError(f'Unrecognized format! For input files {filename}')

    return standard_container(runinfo=standard_runinfo(test='mytest'), data=data)

  @staticmethod
  def from_root(filename):
    with uproot.open(filename) as f:
      # Making settings
      #runinfo_branch = f['run_info']
      #runinfo = {key: runinfo_branch[key] for key in runinfo_branch.keys()}
      # settings = waveform_settings(
      #   **{name: settings[name][0]
      #      for name in settings.fields})
      data = f['DataTree'].arrays()

      return standard_container(runinfo=standard_runinfo(test='none'), data=data)

  def save_to_file(self, filename: str) -> None:
    with uproot.recreate(filename) as f:
      #f['run_info'] = {k: v for k, v in self.runinfo.__dict__.items()}
      f['DataTree'] = {field: self.data[field] for field in self.data.fields}
