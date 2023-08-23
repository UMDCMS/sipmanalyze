"""

estimate.py

Functions to help with estimation of low-light parameters.

"""

import matplotlib.pyplot as plt
import sipmanalyze.formats as forms
import awkward as ak
import numpy as np

import sipmanalyze.plotting as plot
import hist

from scipy.signal import find_peaks
import scipy.integrate as integrate
from scipy.optimize import curve_fit
from scipy.special import factorial


#- Use this function to import the lowlight response data from a root file
#- file_location is a string giving the location of the imported file
#- import_data_results is a dictionary with the results of the import used in later functions:
#  area: raw data
#  amax: max value in area array
#  amin: min value in area array
#  nbins: number of bins in histogram
#  bin_width: width of bin in mv-ns
#  n: number of counts in each bin
#  axis: his.axis object
#  h: histogram object filled with data
def import_data(file_location):
  #get data
  container = forms.waveform.waveform_container.from_root(file_location)
  tint = container.settings.timeintervals
  vadc = container.settings.adc_val
  area = ak.sum(container.waveforms[:, 5:30], axis=-1) * tint * vadc * -1
  amin, amax = ak.min(area), ak.max(area)
  nbins = int((amax - amin) / tint / vadc / 4)
  bin_width=(amax-amin)/nbins
    
  #bin data in histogram
  axis=hist.axis.Regular(nbins, amin, amax, name='r')
  h = hist.Hist(axis)
  h.fill(area)
  
  #save data in dict
  bins, _= h.to_numpy()
  import_data_results={"area":area,"amax":amax,"amin":amin,"nbins":nbins,"bin_width":bin_width, "n":bins, "axis":axis,"h":h}
  return import_data_results

#- use this function to plot the results of importing the data
#- import_data_results is the dictionary of results returned by import_data
def plot_import_data(import_data_results):
  #import histogram data
  h=import_data_results["h"]
  
  #plot histogram data
  fig,ax = plot.make_simple_figure()
  plot.plot_data1d(ax=ax, data=h, label='Data', histtype='fill')
  plot.add_std_label(ax=ax, label='Preliminary', rlabel='Low Light Response')
  ax.set_xlabel('Readout [mV-ns]')
  ax.set_ylabel('Number of events')
  ax.legend()


#- Use this function to determine the location of the peaks in the data, uses https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html
#- import_data_results is the dictionary of results returned by import_data
#- min_gain_guess is the minimum gain expected and helps to avoid extraneous peaks that are too close to each other
#- min_ratio_guess is the minimum height of a peak allowed as a ratio of the highest peak, ensures that tiny fluctutions in the data aren't labeled as peaks
#- return_peak_results is a dictionary of the following info:
# peak_bin_numbers: bin number of each of the peaks
# peaks: center value of the bins where each of the peaks occur in units of mv-ns
def get_peaks(import_data_results, min_gain_guess=80, min_ratio_guess=1/20):  
  #import data
  bin_width=import_data_results["bin_width"]
  n=import_data_results["n"]
  axis=import_data_results["axis"]
  
  #get peaks in data
  min_distance=min_gain_guess/bin_width
  max_occurences=max(n)
  peak_bin_numbers, properties=find_peaks(n,height=max_occurences*min_ratio_guess,distance=min_distance)
  bin_centers=axis.centers
  peaks=bin_centers[peak_bin_numbers]
  peak_results={"peak_bin_numbers":peak_bin_numbers,"peaks":peaks} 
  
  return peak_results

#- use this function to plot the results of importing the data
#- import_data_results is the dictionary of results returned by import_data
#- peak_results is the dictionary of results returned by get_peaks
def plot_peak_results(import_data_results,peak_results):
  #import data
  h=import_data_results["h"] 
  n=import_data_results["n"]  
  peaks=peak_results["peaks"]
  peak_bin_numbers=peak_results["peak_bin_numbers"]

  #plot regular data
  fig,ax = plot.make_simple_figure()
  plot.plot_data1d(ax=ax, data=h, label='Data', histtype='fill')
    
  #plot peak spikes
  ax.vlines(peaks,0,n[peak_bin_numbers],label='Found Peaks',color='red')
    
  #plot labels
  plot.add_std_label(ax=ax, label='Preliminary', rlabel='Low Light Response Peak Finder')
  ax.set_xlabel('Readout [mV-ns]')
  ax.set_ylabel('Number of events')
  ax.legend()

#gauss function used for fitting gaussian peaks
def gauss(x, a, x0, sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))

#- use this function to fit gaussian curves to each of the peaks in the data using curve_fit https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html
#- import_data_results is the dictionary of results returned by import_data
#- peak_results is the dictionary of results returned by get_peaks
#- gauss_width is the number of bins to the left and to the right of the center peak bin which are passed to the gaussian curve fit
#- gauss_dict is the dictionary with the results of the gaussian fittings whose elements are below:
# integral: the integral of each of the gaussian functions from their edges
# peak: the center value of the bin where the peak is located in units of mv-ns
# mu: the mean value of the gaussian curve
# sigma: the standard deviation of the gaussian curve
# a: the factor on the gaussian curve that determines the height of the curve
# x_part: the list of x-locations in mv-ns which were passed to each gaussian fit to determine the curve.
def gauss_estimate(import_data_results, peak_results, gauss_width=10):
  #import data
  amax=import_data_results["amax"]
  amin=import_data_results["amin"]
  bin_width=import_data_results["bin_width"]
  area=import_data_results["area"]
  nbins=import_data_results["nbins"]
  n=import_data_results["n"]
  h=import_data_results["h"]
  peak_bin_numbers=peak_results["peak_bin_numbers"]
  peaks=peak_results["peaks"]

  gauss_dict={"peak":[],"mu":[],"sigma":[],"integral":[],"a":[],"x_part":[]}
  x = np.linspace(amin+bin_width/2, amax-bin_width/2, nbins)
  
  #loop through each peak to attempt to fit gaussian to each
  for idpeak, peak_bin_number in enumerate(peak_bin_numbers):
    #set limits for what data gets passed to each gaussian fitting for each peak
    gauss_width=gauss_width
    min_bin=peak_bin_number-gauss_width
    if(min_bin<0):
      min_bin=0
    max_bin=peak_bin_number+gauss_width+1
    if(max_bin>(nbins-1)):
      max_bin=nbins-1
    x_part=x[min_bin:max_bin]
    n_part=n[min_bin:max_bin]

    #fit gaussian curve
    popt, _ = curve_fit(gauss, x_part, n_part,p0=[10000,peaks[idpeak],50])
 
    #results from gaussian fit
    a=popt[0]
    x0=popt[1]
    sigma=popt[2]

    # Only save data from good gaussian fits
    if abs(x0-peaks[idpeak])<=5*bin_width and sigma<=10*bin_width:
      gauss_dict["integral"].append(integrate.quad(lambda z:gauss(z,a,x0,sigma),x_part[0],x_part[-1])[0])
      gauss_dict["peak"].append(peaks[idpeak])
      gauss_dict["mu"].append(x0)
      gauss_dict["sigma"].append(sigma)
      gauss_dict["a"].append(a)
      gauss_dict["x_part"].append(x_part)
    
  return gauss_dict

#- this function plots the histogram data plus overlays all of the accepted gaussian curves
#- import_data_results is the dictionary of results returned by import_data
#- gauss_dict is the dictionary of results returned by gauss_estimate
def plot_gauss_estimate(import_data_results,gauss_dict):
  #import data
  h=import_data_results["h"]
  
  #plot regular data
  fig,ax = plot.make_simple_figure() 
  plot.plot_data1d(ax=ax, data=h, label='Data', histtype='fill')  
  
  #plot gaussians
  for idpeak, peak in enumerate(gauss_dict["peak"]):
    plt.plot(gauss_dict["x_part"][idpeak], gauss(gauss_dict["x_part"][idpeak],gauss_dict["a"][idpeak],gauss_dict["mu"][idpeak],gauss_dict["sigma"][idpeak]), label='Fit of Peak at '+str(int(peak)))
  
  ##TODO: for some reason running this messes with the plot, it ends up making the whole plot really thin. My issue is that the curve_fit requires using numpy arrays not ax like the other plotting, I'm not sure how to make them more compatible. 
  #plot.add_std_label(ax=ax, label='Preliminary', rlabel='Lowlight Data with Fitted Gaussian Curves for Parameter Estimation')
  ax.set_xlabel('Readout [mV-ns]')
  ax.set_ylabel('Number of events')
  ax.legend()

#- this function determines the estimated vaue of pedestal and gain based on the gaussian curve fits
#- gauss_dict is the dictionary of results returned by gauss_estimate
def pedestal_gain_est(gauss_dict):
  #function which determines the relationship between pedestal, gain, and the mean values of the gaussians
  def linear(z,pedestal,gain):
    return pedestal+z*gain
  #fit mean values of gaussians to function
  popt, popc = curve_fit(linear, range(len(gauss_dict["mu"])), gauss_dict["mu"])
  
  #save data
  pedestal_est=popt[0]
  gain_est=popt[1]
  
  return pedestal_est,gain_est

#- this function determines the estimated vaue of the commmon noise and the pixel noise based on the gaussian curve fits
#- gauss_dict is the dictionary of results returned by gauss_estimate
def common_pixel_noise_est(gauss_dict):
  #function which determines the relationship between the common noise, the pixel noise, and the gaussian standard deviation
  def noise(z,common_noise,pixel_noise):
    return np.sqrt(common_noise*common_noise+z*pixel_noise*pixel_noise)

  #fit function to gaussian standard deviations
  popt, popc = curve_fit(noise,range(len(gauss_dict["sigma"])),gauss_dict["sigma"],bounds=(0,100))
  
  #save data
  common_noise_est=popt[0]
  pixel_noise_est=popt[1]
    
  return common_noise_est, pixel_noise_est

#- this function determines the estimated vaue of the poisson mean and the poisson borel based on the gaussian curve fits
#- gauss_dict is the dictionary of results returned by gauss_estimate
def poisson_mean_borel_est(gauss_dict):
  #function which determines the relationship between the poisson mean, the poisson borel, the number of events, and the number of events under each gaussian curve
  def height(z,N,mu,l):
    y=(mu+(z*l))
    result=np.exp(-np.log(factorial(z))+np.log(mu)+np.log(N)+(z-1)*np.log(y)-y)
    return result
  
  
  #used to scale the gaussian to the correct size by setting the value of N instead of using fractional probabilities
  integrals_total=sum(gauss_dict["integral"])
  
  #fit integral values to the function
  popt, popc = curve_fit(height,np.arange(stop=len(gauss_dict["integral"]),step=1),gauss_dict["integral"],p0=(integrals_total,2.5,.05),bounds=([integrals_total-50000,.1,0],[integrals_total+50000,5,.2]))
  
  #saving data
  poisson_mean_est=popt[1]
  poisson_borel_est=popt[2]

  return poisson_mean_est, poisson_borel_est
