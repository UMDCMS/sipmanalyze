"""

estimate.py

Functions to help with estimation of low-light parameters.

"""

import sys
sys.path.insert(0, '../../sipmpdf')
sys.path.insert(0, '../')

import matplotlib.pyplot as plt
import src.sipmanalyze.formats as forms
import awkward as ak
import numpy as np

from scipy.signal import find_peaks
import scipy.integrate as integrate
from scipy.optimize import curve_fit


def import_data(file_location,plot=True):
  container = forms.waveform.waveform_container.from_root(file_location)
  tint = container.settings.timeintervals
  vadc = container.settings.adc_val
  area = ak.sum(container.waveforms[:, 5:30], axis=-1) * tint * vadc * -1
  amin, amax = ak.min(area), ak.max(area)
  nbins = int((amax - amin) / tint / vadc / 4)

  n, bins, patches= plt.hist(x=area, bins=nbins, range=(amin, amax), label='r')
  total_elements=sum(n)
  bin_width=(amax-amin)/nbins
  
  if plot:
    plt.title("Lowlight Data")
    plt.xlabel('Readout value mv-ns')
    plt.ylabel('Number of events')
    plt.legend()
   
  results={"raw_data":area,"amax":amax,"amin":amin,"nbins":nbins,"bin_width":bin_width, "n":n,}
  return results



def get_peaks(import_data_results, plot=True, min_gain_guess=80, min_ratio_guess=1/20):  

  n=import_data_results["n"]
  amax=import_data_results["amax"]
  amin=import_data_results["amin"]
  bin_width=import_data_results["bin_width"]
    
  min_distance=min_gain_guess/bin_width
  max_occurences=max(n)
  binned_peaks, properties=find_peaks(n,height=max_occurences*min_ratio_guess,distance=min_distance)
   
  if plot:
    plt.plot(n,label="Rebinned Data")
    plt.plot(binned_peaks, n[binned_peaks], "x",label="Found Peaks")
    plt.plot(np.zeros_like(n), "--", color="gray")
    plt.xlabel('Bin Number')
    plt.ylabel('Number of Occurences')
    plt.title('Peaks Found on Rebinned Data')
    plt.legend()
    plt.show()

  return binned_peaks
 

def gauss_estimate(import_data_results, peak_bin_numbers, gauss_width=10, plot=True):
  def gauss(x, a, x0, sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))
  amax=import_data_results["amax"]
  amin=import_data_results["amin"]
  bin_width=import_data_results["bin_width"]
  raw_data=import_data_results["raw_data"]
  nbins=import_data_results["nbins"]
  n=import_data_results["n"]
    
  x = np.linspace(amin+bin_width/2, amax-bin_width/2, nbins)
  gauss_dict={"peak":[],"mu":[],"sigma":[],"integral":[]}
  adjusted_peaks=peak_bin_numbers*bin_width+amin
  if plot: plt.hist(raw_data,bins=400,label="Raw Data")

  for idpeak, peak in enumerate(adjusted_peaks):
  
    peak_bin_number=int(peak_bin_numbers[idpeak])
    gauss_width=gauss_width
    min_bin=peak_bin_number-gauss_width
    if(min_bin<0):
      min_bin=0
    max_bin=peak_bin_number+gauss_width+1
    if(max_bin>(nbins-1)):
      max_bin=nbins-1
    
    x_part=x[min_bin:max_bin]
    n_part=n[min_bin:max_bin]

    popt, _ = curve_fit(gauss, x_part, n_part,p0=[10000,peak,50])
 
    a=popt[0]
    x0=popt[1]
    sigma=popt[2]

    # Only save and plot data from good gaussian fits
    if abs(x0-peak)<=5*bin_width and sigma<=10*bin_width:
      if plot: plt.plot(x_part, gauss(x_part,a,x0,sigma), label='Fit of Peak at '+str(int(peak)))
      gauss_dict["integral"].append(integrate.quad(lambda z:gauss(z,a,x0,sigma),x_part[0],x_part[-1])[0])
      gauss_dict["peak"].append(peak)
      gauss_dict["mu"].append(x0)
      gauss_dict["sigma"].append(sigma)
    
  #plot results
  if plot:
    plt.xlabel('Readout value mv-ns')
    plt.ylabel('Number of events')
    plt.legend()
    plt.title('Lowlight Data with Fitted Gaussian Curves for Parameter Estimation')
    
  return gauss_dict
 