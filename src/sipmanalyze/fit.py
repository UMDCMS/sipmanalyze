"""

fit.py

User-level function to simplify for common fitting routines using PDF objects
defined in sipmpdf.

"""

from typing import Any, Dict, Tuple, Union

import hist
import numpy
import sipmpdf.pdf
import zfit


# - This funciton ensures that any upper and lower bounds passed to zfit are reasonable
# - variable_estimates is the dictionary of estimates for each variable with the key as the variable name
# - limits_dict is a user set dictionary where each key is the name of each variable:
#   - The content of each element of the dictionary is another dictionary which has "width": the distance from the estimation the bounds should be, and the optional values of "upper_max" and "lower_max" which provide the logical limits which a variable value may not cross.
# - returns limits_dict where the keys are the names of each of the variables, and the value is a dictionary:
#     width: the distance from the estimation the upper and lower bounds should be
#     upper_max: the maximum value allowed by logic for a variable
#     lower_max: the minimum value allowed by logic for a variable
#     upper_bound: the upper bound passed to zfit to try while fitting
#     lower_bound: the lower bound passed to zfit to try while fitting
def set_bounds(variable_estimates, limits_dict):
    for key, value in variable_estimates.items():
        # error testing
        if key not in limits_dict:
            raise Exception("The variable ", key, "is not in the limits_dict")
        if "width" not in limits_dict[key]:
            raise Exception(
                "The width is not set in limits_dict for the variable ", key
            )
        if limits_dict[key]["width"] <= 0:
            raise Exception("width <= 0 in limits_dict for the variable ", key)

        # calculate correct bounds
        lower_bound = value - limits_dict[key]["width"]
        upper_bound = value + limits_dict[key]["width"]
        if "lower_max" in limits_dict[key]:
            if lower_bound < limits_dict[key]["lower_max"]:
                lower_bound = limits_dict[key]["lower_max"]
        if "upper_max" in limits_dict[key]:
            if upper_bound > limits_dict[key]["upper_max"]:
                upper_bound = limits_dict[key]["upper_max"]
        limits_dict[key]["upper_bound"] = upper_bound
        limits_dict[key]["lower_bound"] = lower_bound

    return limits_dict


def __create_obs_from_hist(
    data_hist: hist.Hist,
) -> Tuple[zfit.Space, zfit.Space, zfit.data.BinnedData]:
    """
    Creating the observable space and the binned dataset based on the a
    histogram object.
    """
    data_axis = data_hist.axes[0]
    obs = zfit.Space(data_axis.name, limits=(
        data_axis.edges[0], data_axis.edges[-1]))
    binning = zfit.binned.RegularBinning(
        len(data_axis), data_axis.edges[0], data_axis.edges[-1], name=data_axis.name
    )
    obs_bin = zfit.Space(data_axis.name, binning=binning)
    zfit_data_binned = zfit.data.BinnedData.from_hist(data_hist)
    return obs, obs_bin, zfit_data_binned
    pass


__response_var_list__ = (
    [  # List of objects that should be either fixed or left floating
        "pedestal",
        "gain",
        "common_noise",
        "pixel_noise",
        "poisson_mean",
        "poisson_borel",
        "ap_beta",
        "ap_prob",
        "dc_prob",
        "dc_res",
    ]
)


def create_response_pdf_data(
    data_hist: hist.Hist,
    parameters: Dict[
        str, Union[float, Tuple[float],
                   Tuple[float, float], Tuple[float, float, float]]
    ],
    routine_name: str = "fixed_param",
) -> Dict[str, Any]:
    """
    Running the fit with a list of set of parameters, for each of the
    parameters used to define the response PDF, the value can either be a
    singular value (fixed parameter), a central value with a +- range, or a
    central value with an upper and lower limit.
    """
    param_dict = {}  # Container to pass to underlying routines
    for var in __response_var_list__:
        assert (
            var in parameters.keys()
        ), f"Parameters setting not found for variable {var}!"

        if (
            type(parameters[var]) is float
            or type(parameters[var]) is numpy.float64
            or len(parameters[var]) == 1
        ):
            param_dict[var] = zfit.param.ConstantParameter(
                var + routine_name, parameters[var]
            )
        elif len(parameters[var]) == 2:
            cen, ran = parameters[var]
            param_dict[var] = zfit.Parameter(
                var + routine_name, cen, cen -
                numpy.abs(ran), cen + numpy.abs(ran)
            )
        elif len(parameters[var]) == 3:
            cen, lo, up = parameters[var]
            param_dict[var] = zfit.Parameter(var + routine_name, cen, lo, up)
        else:
            raise ValueError(
                "Floating parameters needs to be 1 value (fixed value), 2 values (central + range) or 3 (central, lower bound, upper bound)"
            )
    obs, obs_bin, zfit_data_binned = __create_obs_from_hist(data_hist)
    pdf_unbinned = sipmpdf.pdf.SiPMResponsePDF(obs=obs, **param_dict)
    pdf_binned = zfit.pdf.BinnedFromUnbinnedPDF(pdf_unbinned, obs_bin)
    return pdf_unbinned, pdf_binned, zfit_data_binned


def update_response_parameter_bounds(
    parameters: Dict[
        str, Union[float,
                   Tuple[float],
                   Tuple[float, float],
                   Tuple[float, float, float],]
    ],
    result,
    relative_range: float = 0.3,
    fit_uncer_range: float = 3.0,
) -> Dict[str, Tuple[float, float, float]]:
    """
    Given the original dictionary representing the response parameters, update
    according to the desired relative range and the fitting results.
    """
    param_dict = {}  # Container to pass to underlying routines

    # Getting the alias to the underlying results
    minuit = result.info["minuit"]
    fit_params = [x for x in minuit.var2pos]
    for var in __response_var_list__:
        assert (
            var in parameters.keys()
        ), f"Parameters setting not found for variable {var}!"

        # Getting the central values
        cen = None
        if (
            type(parameters[var]) is float
            or type(parameters[var]) is numpy.float64
            or len(parameters[var]) == 1
        ):
            cen = parameters[var]
        for k in fit_params:
            if k.startswith(var):
                cen = minuit.values[k]
                break
        # Getting the uncertainties
        unc = relative_range * cen
        for k in fit_params:
            if k.startswith(var):
                unc = fit_uncer_range * minuit.errors[k]
                break

        param_dict[var] = [cen, cen - unc, cen + unc]

    return param_dict
