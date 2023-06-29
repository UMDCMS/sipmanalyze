"""

plotting.py

Helper functions for unifying the plotting routines, providing the common
styling methods.

"""
from typing import Tuple, Union, Optional
from decimal import Decimal

import matplotlib as matplot
import mplhep
import hist
import hist.intervals
import boost_histogram

import numpy as np
import zfit


def make_simple_figure():
  """
  Making the simple figure, axis instance for plotting
  """
  matplot.pyplot.style.use(mplhep.style.CMS)
  fig = matplot.pyplot.figure(constrained_layout=True)
  spec = fig.add_gridspec(ncols=1, nrows=1, width_ratios=[1], height_ratios=[1])
  ax = fig.add_subplot(spec[0, 0])
  ax.set_xlabel('', horizontalalignment='right', x=1.0)
  ax.set_ylabel('', horizontalalignment='right', y=1.0)
  return fig, ax


def make_ratio_figure():
  """
  Making a standard ratio plot figure using matplotlib.

  The top and bottom axes objects with share the same x axes, with the axes tile
  and tick labels already tweaked for the standard ratio plots format. The top
  axes object will be square, and the bottom axes object will have a 1:2 ratio.
  """
  matplot.style.use(mplhep.style.CMS)
  fig = matplot.pyplot.figure(constrained_layout=True)
  spec = fig.add_gridspec(ncols=1,
                          nrows=2,
                          width_ratios=[1],
                          height_ratios=[3, 1])
  ax_upper = fig.add_subplot(spec[0, 0])
  ax_lower = fig.add_subplot(spec[1, 0], sharex=ax_upper)

  ## Common settings
  matplot.pyplot.setp(ax_upper.get_xticklabels(), visible=False)
  ax_lower.set_xlabel('', horizontalalignment='right', x=1.0)
  ax_lower.set_ylabel('', horizontalalignment='center', y=0.5)
  ax_upper.set_ylabel('', horizontalalignment='right', y=1.0)
  return fig, (ax_upper, ax_lower)


def _get_range1d(pdf, data=None, prange=None):
  """Getting the 1D plotting range"""
  if prange is not None:
    return prange  # Custom range
  elif data is not None:
    if isinstance(data, zfit.core.data.Data):
      return tuple(data.data_range.limit1d)
    elif isinstance(data, zfit._data.binneddatav1.BinnedData):
      return tuple(data.data_range.limit1d)
    elif isinstance(data, hist.BaseHist):
      return data.axes[0]

  else:
    return tuple(pdf._space.limit1d)


def _get_norm1d(prange, data=None) -> float:
  """
  Calculating the normalization factor for the plotted PDF given the data.

  For a binned data set with regular bin width, this normalization factor will
  be given as: s * w, where s is the entry count of the data within the
  specified plot range, and w with the bin width.

  For data with variable binning, the extra bin-width factor will not be added,
  instead the histogram should be modified such that it plots the effective
  density of each bin entry by divide each bin entry by the bin width before
  plotting.
  """
  if data is None:
    return 1.0
  elif isinstance(data, zfit._data.binneddatav1.BinnedData):
    # Binned data set in zfit, casting to hist to typical conversion
    return _get_norm1d(prange, data.to_hist())
  elif isinstance(data, hist.BaseHist):
    assert len(data.axes) == 1, "Only 1 dimensional histograms allowed!"
    # Getting the sum of weights
    s = data[prange[0] * 1j:prange[1] * 1j:sum]
    if isinstance(s, boost_histogram.accumulators.WeightedSum):
      s = s['value']
    if isinstance(data.axes[0], hist.axis.Regular):
      s = s * np.mean(data.axes.widths[0])

    return s

  warnings.warn(
    'Unsupported data type used specify normalization, no normalization will be calculated',
    UserWarning)
  return 1.0


def unbinned_to_binned(data, binning, prange=None):
  """
  Converting an unbinned data to a binned data collection for plotting.
  """
  raise NotImplementedError('Not implement!')


def _calc_pdf_arrays(x, pdf, data, prange=None, binning: int = 40):
  if isinstance(data, zfit.data.Data):
    data = unbinned_to_binned(data, binning, prange=prange)
    return _calc_pdf_arrays(x, pdf, data, prange=prange, binning=binning)
  else:
    y = pdf.pdf(x)  # Regular PDF calculations
    y = y * _get_norm1d(prange, data)  # Scaling to data
    return y
  pass


def plot_pdf1d(ax,
               pdf,
               data=None,
               scale: float = 1,
               prange: Optional[Tuple[int, int]] = None,
               binning: int = 40,
               **kwargs):
  """
  Plotting a zfit pdf model onto a canvas. Data is here to matched the
  normalization, kwargs are passed as is to the underlying `ax.plot` method.

  Parameters
  ----------
  ax : matplotlib axes object
      Axes where the PDF will be plotted
  pdf : zfit.pdf type object
      PDF the you wish to plot
  data : data container PDF normalization.
      This can either be a hist.BaseHist object or a zfit.Data object (both
      unbinned and binned are acceptable). If non is provided, then no
      normalization will be performed (PDF will integrate to 1 in the
      observables defined range)
  scale : float, optional
      Additional normalization factor to add on top toe the normalization factor
      defined by the data container. Useful is you want to plot individual
      components of a summed PDF, by default 1 (no additional scaling).
  prange : _type_, optional
      Overriding the plot range, if not provided, the plotting range will be
      determined by the given data, or if data is also not given, the PDF range.
  binning : int, optional
      Number of bins used use when extracting normalization from unbinned data.
      Notice that only regular binning will be used in this case.

  Returns
  -------
  returns the x,y numpy arrays used to plot the PDF function.
  """
  if isinstance(data, zfit.data.Data):
    ## Processing required for unbinned data,
    data = unbinned_to_binned(data, binning, prange=prange)
    return plot_pdf1d(ax=ax,
                      pdf=pdf,
                      data=data,
                      scale=scale,
                      prange=prange,
                      **kwargs)
  else:
    prange = _get_range1d(pdf, data, prange)
    x = np.linspace(prange[0], prange[1], num=2000)
    y = _calc_pdf_arrays(x, pdf, data, prange)  # Regular PDF calculations
    y = y * scale  # Additional scale factor
    ax.plot(x, y, **kwargs)  # Running the plot
    return x, y


def _calc_density_hist(h):
  """
  Scaling the bin value of each histograms according to the bin width. And
  returning a temporary histogram to be used in plotting. The original histogram
  will remain unmodified.
  """
  raise NotImplementedError('')


def plot_data1d(ax, data, **kwargs):
  """
  Plotting 1 dimensional data containers

  First we will cast everything to hist.Hist objects, then we check to see if
  variable binning is used, if yes, then a modified histogram will be plotted
  instead, where each of the bin entries is divided by the bin width, that way,
  the histogram is ensured to have reliable scaling with data.
  """
  if isinstance(data, zfit.data.Data):
    binned_data = unbinned_to_binned(data,
                                     binning=kwargs.pop('binning'),
                                     prange=kwargs.pop('prange'))
    return plot_data1d(ax, binned_data)
  elif isinstance(data, zfit._data.binneddatav1.BinnedData):
    return plot_data1d(ax, data.to_hist())
  elif isinstance(data, hist.Hist):
    assert len(data.axes) == 1, "Can only plot 1d histograms"
    if isinstance(data.axes[0], hist.axis.Regular):
      pdata = data
    else:
      pdata = _calc_density_hist(data)
    mplhep.histplot(pdata, ax=ax, **kwargs)
  else:
    raise NotImplementedError('Unknown data type!')


def plot_fitratio(ax, num, den, prange=None, **kwargs):
  """
  Plotting the fit results ratio comparison.
  """
  pnum = num.copy()  # Making a copy of the histogram

  # Getting the Poisson uncertainties
  p_lo, p_up = hist.intervals.poisson_interval(pnum.values(), pnum.variances())
  p_lo = pnum.values() - p_lo
  p_up = p_up - pnum.values()

  # Modifying the range
  prange = _get_range1d(den, data=num, prange=prange)

  # Getting the relevant pdf values
  x = pnum.axes[0].centers
  y = _calc_pdf_arrays(x, den, num, prange)

  # Scaling values within range
  pnum.values()[:] = np.where((x >= prange[0]) & (x <= prange[1]),
                              pnum.values() / y, np.nan)

  # Running the plot call
  mplhep.histplot(pnum, ax=ax, yerr=[p_lo / y, p_up / y], **kwargs)
  return pnum


def number_str(central: float,
               unc: Union[Tuple[float, float], float],
               *args,
               nsig=2,
               align_str='',
               scientific=False) -> str:
  """
  Converting numerical results with uncertainties to a CMS recommended number
  format.

  The *args input can be an arbitrary list of uncertainties. Uncertainties can
  either by a 2-tuple of asymmetric uncertainties (where the uncertainties will
  be indicated using the ${}^{+}_{-}$ format), or a singular floating point
  number indicating the symmetric uncertainty (where the uncertainty will be
  indicated using the ${}\pm{}$ format).

  Numbers are all rounded such that the largest uncertainty displays `nsig`
  significant digits or at-least 1 digit below the decimal place. If the
  scientific notation is set to true, all uncertainty values are first scaled
  according to the exponent of the central value, and the appropriate
  $\times10^{n}$ will be added to the string.
  """
  def b10_exp_single(number):
    (sign, digits, exponent) = Decimal(number).as_tuple()
    return len(digits) + exponent - 1

  def b10_exp(*args):
    return tuple(b10_exp_single(x) for x in args)

  if not scientific:
    unc_exp = np.max([
      np.max(b10_exp(*u) if isinstance(u, tuple) else b10_exp(u))
      for u in [unc, *args]
    ])
    ndigit = np.max([(unc_exp - nsig + 1) * -1, 1])
    fmt = "{{:.{ndigit}f}}".format(ndigit=ndigit)

    def tuple_str(t):
      assert len(t) == 2
      prod = (t[0] * t[1])
      if prod < 0:
        uplo_fmt = '{{{{}}}}^{{{{+{fmt}}}}}_{{{{-{fmt}}}}}'.format(fmt=fmt)
        return uplo_fmt.format(np.abs(np.max(t)), np.abs(np.min(t)))
      else:
        if np.max(t) >= 0:
          uu_fmt = '{{{{}}}}^{{{{+{fmt}}}}}_{{{{+{fmt}}}}}'.format(fmt=fmt)
          return uu_fmt.format(np.abs(np.max(t)), np.abs(np.min(t)))
        else:
          ll_fmt = '{{{{}}}}^{{{{-{fmt}}}}}_{{{{-{fmt}}}}}'.format(fmt=fmt)
          return ll_fmt.format(np.abs(np.max(t)), np.abs(np.min(t)))

    def single_str(n):
      single_fmt = '\pm{{{fmt}}}'.format(fmt=fmt)
      return single_fmt.format(n).format(n)

    tokens = [
      fmt.format(central), *[
        tuple_str(x) if isinstance(x, tuple) else single_str(x)
        for x in [unc, *args]
      ]
    ]

    if align_str:
      return align_str.join(['$' + x + '$' for x in tokens])
    else:
      return '$' + align_str.join(tokens) + '$'

  else:
    ex = b10_exp_single(central)
    shift = 10**ex

    def shift_num(x):
      if isinstance(x, tuple):
        return tuple(shift_num(n) for n in x)
      else:
        return x / shift

    s = number_str(shift_num(central),
                   *shift_num((unc, *args)),
                   nsig=nsig,
                   align_str='',
                   scientific=False)
    if ex != 0:
      return '$(' + s[1:-1] + f')\\times 10^{{{ex:d}}}$'
    else:
      return s


def add_std_label(ax, label=None, **kwargs):
  """
  Typical labels to be added onto the plot. Borrowing the CMS format for now.
  """
  kwargs.setdefault('loc', 2)  # Top left corner multiline
  kwargs.setdefault('rlabel', '(Light source)')
  kwargs.setdefault('exp', 'HGCAL')
  kwargs.setdefault('data', True)
  mplhep.cms.label(ax=ax, label=label, **kwargs)
  try:
    mplhep.plot.ylow(ax)
  except:
    pass

  # Automatically scaling the axis according to legend
  if ax.legend_ is not None:
    try:
      mplhep.plot.yscale_legend(ax=ax)
    except:
      print('Warning, autosetting y failed, you might want to `ax.set_ylim`')
      pass
  # Additional adjustments for data
  try:
    mplhep.plot.yscale_text(ax=ax)
  except:
    pass

  # Scaling to accommodate additional text boxes (wrapped as text might not be
  # present)
  #while hep.plot.overlap(ax, _text_bbox(ax)) > 0:
  #  ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[-1] * 1.1)
  #  ax.figure.canvas.draw()
  return ax


def datastyle(**kwargs):
  default_args = dict(color='k', marker='o', markersize=10, zorder=1000)
  default_args.update(kwargs)
  return default_args