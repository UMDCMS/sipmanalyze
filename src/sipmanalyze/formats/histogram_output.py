"""

Casting the various output to a standard histogram format. The output should
always be a 1D histogram with a single axis 

"""
import awkward
import hist

from .waveform import waveform_container


def from_waveform(
    file_location: str, start: int, stop: int, invert: bool = True, bin_group: int = 4
):
    """
    Converting from the waveform readout format
    """
    container = waveform_container.from_root(file_location)

    # Getting the intergration using slicing
    int_slice = slice(start, stop)
    area = awkward.sum(container.waveforms[:, int_slice], axis=-1)

    # Converting to user readable format
    tint = container.settings.timeintervals
    vadc = container.settings.adc_val
    mult = -1 if invert else 1
    area = area * tint * vadc * mult

    # Setting up the binning scheme
    amin, amax = awkward.min(area), awkward.max(area)
    nbins = int((amax - amin) / tint / vadc / bin_group)

    # bin data in histogram
    h = hist.Hist(hist.axis.Regular(nbins, amin, amax, name="Readout [mV-ns]"))
    h.fill(area)

    return h
