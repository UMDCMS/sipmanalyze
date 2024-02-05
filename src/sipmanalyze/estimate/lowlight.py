"""

Methods for extracting the minimum estimating function parameters for the low
light fit.

"""
from typing import Dict, List

import hist
import numpy
# Scipy functions for signal extraction
import scipy.optimize
import scipy.signal
import sipmpdf.functions


def estimate_peaks(h_data: hist.Hist, min_gain=80, min_ratio: float = 0.05):
    """
    Getting the esitmated peak positions using the scipy.signal.find_peaks
    given a histogram of interest.

    - min_gain: The minimum distance between the peaks that should be
      considered by the peak finding algorithm (>0).
    - min_ratio: The minimum value relative to the largest entry in the
      histogram that is taken into consideration as a peak.

    Returns a list of peak positions in terms of bin center values
    """
    assert min_gain > 0, "Minimum gain estimate must be greater than 0"
    assert 0 < min_ratio < 1, "Minimum peak ratio must be between 0 and 1"

    # Getting some binning information
    bin_centers = h_data.axes[0].centers
    bin_width = h_data.axes[0].widths[0]  # Assuming equal width binning

    # Running the peak finding algorithm
    peak_bin_numbers, _ = scipy.signal.find_peaks(
        h_data.view(),
        height=numpy.max(h_data.view()) * min_ratio,
        distance=min_gain / bin_width,
    )
    # Returning in terms of the direct results
    return bin_centers[peak_bin_numbers]


def estimate_gauss_param(
    h_data: hist.Hist, peak_positions: numpy.ndarray, fit_bin_count: int = 10
) -> Dict[str, List]:
    """
    Extracting the Guassian parameters of this histogram at the estimated peak
    positions using a simple [`scipy.optimize.curve_fit`][curve_fit] method

    Inputs:
        - `h_data`: The data in 1D histogram format.
        - `peak_positions`: Extracted peak positions using the `estimate_peak
          function`
        - `gauss_width`: Number of bins to take into consideration when running
          the local Gaussian fits.

    Output is a dictionary of a list of number of the variouls Gaussian fitting
    results. The stored results include:
        - peak_id: The integer index of the fitted peak in the listed of peak
          positions.
        - mu: the mean value of the gaussian curve
        - sigma: the standard deviation of the gaussian curve
        - norm: the normalization factor of the gaussian curve
        - x_range: the min/max values used to perform the fit

    [curve_fit]: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html
    """
    # error testing
    assert type(fit_bin_count) is int, "Guass width in units of bin counts"
    assert fit_bin_count > 0, "Initial guassian guess should be > 0"

    def gauss(x, norm, x0, sigma):
        return norm * sipmpdf.functions.normal(x, x0, sigma)

    # Return data format
    return_dict = {
        "peak_id": [],
        "mu": [],
        "sigma": [],
        # "integral": [],
        "norm": [],
        "xrange": [],
    }
    x_axis = h_data.axes[0]
    bin_width = x_axis.widths[0]  # Assumining common width

    # loop through each peak to attempt to fit gaussian to each
    peak_bin_numbers = numpy.digitize(peak_positions, x_axis.edges) - 1
    for peak_id, (peak_bin, peak_cen) in enumerate(
        zip(peak_bin_numbers, peak_positions)
    ):
        # Setting the fit x ranges
        min_bin = numpy.max([peak_bin - fit_bin_count, 0])
        max_bin = numpy.min([peak_bin + fit_bin_count, len(x_axis) - 1])

        x_arr = x_axis.centers[min_bin:max_bin]
        y_arr = h_data.view()[min_bin:max_bin]

        # fit gaussian curve
        (norm, x0, sig), _ = scipy.optimize.curve_fit(
            gauss, x_arr, y_arr, p0=[10000, peak_cen, 10]
        )

        # Only save data from good gaussian fits
        if (x0 - peak_cen) >= 5 * bin_width:
            continue  # Skipping!!
        if sig >= 10 * bin_width:
            continue

        # return_dict["integral"].append(
        #    integrate.quad(lambda z: gauss(z, a, x0, sigma), x_part[0], x_part[-1])[0]
        # )

        return_dict["peak_id"].append(peak_id)
        return_dict["mu"].append(x0)
        return_dict["sigma"].append(sig)
        return_dict["norm"].append(norm)
        return_dict["xrange"].append((x_arr[0], x_arr[-1]))

    return return_dict


def estimate_pedestal_gain(gauss_estimate_dict: Dict[str, List]) -> Dict[str, float]:
    """
    Extracting the pedestal and gain by linear fitting the position of the
    local Gaussian fits.
    """

    def linear(z, pedestal, gain):
        return pedestal + z * gain

    # fit mean values of gaussians to function
    (ped, gain), popc = scipy.optimize.curve_fit(
        linear, gauss_estimate_dict["peak_id"], gauss_estimate_dict["mu"]
    )
    return {"pedestal": ped, "gain": gain}


def estimate_noise_param(gauss_dict: Dict[str, List]) -> Dict[str, float]:
    """
    Estimating the Gaussian noise parameters from the width developement of
    local Gaussian fits.
    """

    def noise(z, s0, s1):
        return numpy.sqrt(s0 * s0 + z * s1 * s1)

    # fit function to gaussian standard deviations
    (s0, s1), popc = scipy.optimize.curve_fit(
        noise, gauss_dict["peak_id"], gauss_dict["sigma"], bounds=(0, 100)
    )

    return {"common_noise": s0, "pixel_noise": s1}


def estimate_poisson(gauss_dict: Dict[str, List]) -> Dict[str, float]:
    """
    Estimating the Possion distribution based on the normalaziation results of
    the local Gaussian fits.
    """

    def gen_poisson(z, N, mu, lam):
        return N * sipmpdf.functions.generalized_poisson(z, mu, lam)

    x = numpy.array(gauss_dict["peak_id"])
    norm = numpy.array(gauss_dict["norm"])
    s = numpy.sum(norm)

    # fit integral values to the function
    (norm, mu, lam), popc = scipy.optimize.curve_fit(
        gen_poisson,
        x,
        norm,
        p0=(s, numpy.sum(x * norm) / s, 0.00),
        bounds=([0, 0.01, 0], [s * 1.5 + 50000, 10, 0.2]),
    )

    return {"poisson_total": norm, "poisson_mean": mu, "poisson_borel": lam}
