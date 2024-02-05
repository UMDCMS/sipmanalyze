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
class waveform_settings:
    """
    Settings used during the data collection routine
    """

    timeintervals: Union[awkward.Array, float]
    triggerdelay: float
    adc_val: float
    adc_bits: int
    invert: True


__adc_dtype_dict__ = {
    2: numpy.int8,
    4: numpy.int16,
}


@dataclass
class waveform_container:
    settings: waveform_settings
    waveforms: awkward

    @staticmethod
    def from_txt(filepath: str):
        """
        Getting the waveform data from a plain text file.

        The first line of the file will be either 5 numbers or 3 numbers, indicating
        the data collection and trigger setup. The next lines will be the waveform
        encoded in hex format.
        """
        with open(filepath, "r") as f:
            """Getting the settings line"""
            settings_line = f.readline().split()
            if len(settings_line) == 5:  # This is the old format with 5 inputs.
                settings = waveform_settings(
                    timeintervals=float(settings_line[0]),
                    triggerdelay=int(0),
                    adc_val=float(settings_line[4]) * 256,
                    adc_bits=int(2),
                    invert=True,
                )
            elif len(settings_line) == 3:  # New DRS format
                settings = waveform_settings(
                    timeintervals=float(settings_line[2]),
                    triggerdelay=int(0),
                    adc_val=float(settings_line[0]),
                    adc_bits=int(settings_line[1]),
                    invert=True,
                )
            else:
                raise RuntimeError(f"Unknown settings format in {filepath}.")

            """Processing the Waveforms"""

            def convert_line(line, idx):
                print(f"\rRunning events {idx}...", end="")
                return numpy.array(
                    [
                        int(line[i : i + settings.adc_bits], 16)  # Folding the results
                        for i in range(0, len(line), settings.adc_bits)
                    ]
                ).astype(__adc_dtype_dict__[settings.adc_bits])

            waveforms = awkward.values_astype(
                awkward.Array(
                    [convert_line(line.strip(), idx + 1) for idx, line in enumerate(f)]
                ),
                __adc_dtype_dict__[settings.adc_bits],
            )
            print(waveforms.__repr__)

            return waveform_container(settings=settings, waveforms=waveforms)

    @staticmethod
    def from_root(filename: str):
        with uproot.open(filename) as f:
            # Making settings
            settings = f["run_info/readout"].arrays()
            settings = waveform_settings(
                **{name: settings[name][0] for name in settings.fields}
            )
            waveforms = f["DataTree"].arrays()["waveforms"]

            return waveform_container(settings=settings, waveforms=waveforms)

    def save_to_file(self, filename: str) -> None:
        """
        Saving the waveform to root.
        """
        with uproot.recreate(filename) as f:
            f["run_info/readout"] = {
                k: numpy.array([v]) for k, v in self.settings.__dict__.items()
            }
            f["DataTree"] = {"waveforms": self.waveforms}
