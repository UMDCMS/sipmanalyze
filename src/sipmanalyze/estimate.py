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

import zfit


#- Use this function to import the lowlight response data from a root file
#- file_location is a string giving the location of the imported file
#- import_data_results is a dictionary with the results of the import used in later functions:
#      area: raw data
#      h: histogram object filled with data
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
  import_data_results={"area":area,"h":h}
  return import_data_results

#- use this function to plot the results of importing the data
#- import_data_results is the dictionary of results returned by import_data
#- fig, ax are the figure and axis respectively of the plot so the user may make further edits to the plot
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
  
  return fig, ax


#- Use this function to determine the location of the peaks in the data, uses https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html
#- import_data_results is the dictionary of results returned by import_data
#- min_gain_guess is the minimum gain expected and helps to avoid extraneous peaks that are too close to each other
#- min_ratio_guess is the minimum height of a peak allowed as a ratio of the highest peak, ensures that tiny fluctutions in the data aren't labeled as peaks
#- return_peak_results is a dictionary of the following info:
#     peak_bin_numbers: bin number of each of the peaks
#     peaks: center value of the bins where each of the peaks occur in units of mv-ns
def get_peaks(import_data_results, min_gain_guess=80, min_ratio_guess=1/20):  
  #error testing
  if min_gain_guess <=0:
    raise Exception("min_gain_guess must be greater than or equal to 0, current value is ",min_gain_results)
  if min_ratio_guess<0 or min_ratio_guess >1:
    raise Exception("min_ratio_guess must be from 0 to 1, current value is ",min_ratio_guess)
 
  #import data
  h=import_data_results["h"]
  n, _= h.to_numpy()
  axis=h.axes[0]
  bin_centers=axis.centers
  nbins=len(bin_centers)
  bin_width=(axis.edges[-1]-axis.edges[0])/nbins
  
  #get peaks in data
  min_distance=min_gain_guess/bin_width
  max_occurences=max(n)
  peak_bin_numbers, properties=find_peaks(n,height=max_occurences*min_ratio_guess,distance=min_distance)
  peaks=bin_centers[peak_bin_numbers]
  peak_results={"peak_bin_numbers":peak_bin_numbers,"peaks":peaks} 
  
  return peak_results

#- use this function to plot the results of importing the data
#- import_data_results is the dictionary of results returned by import_data
#- peak_results is the dictionary of results returned by get_peaks
#- fig, ax are the figure and axis respectively of the plot so the user may make further edits to the plot
def plot_peak_results(import_data_results,peak_results):
  #import data
  h=import_data_results["h"] 
  n, _= h.to_numpy() 
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

  return fig, ax

#gauss function used for fitting gaussian peaks
def gauss(x, a, x0, sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))

#- use this function to fit gaussian curves to each of the peaks in the data using curve_fit https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html
#- import_data_results is the dictionary of results returned by import_data
#- peak_results is the dictionary of results returned by get_peaks
#- gauss_width is the number of bins to the left and to the right of the center peak bin which are passed to the gaussian curve fit
#- gauss_dict is the dictionary with the results of the gaussian fittings whose elements are below:
#     integral: the integral of each of the gaussian functions from their edges
#     peak: the center value of the bin where the peak is located in units of mv-ns
#     mu: the mean value of the gaussian curve
#     sigma: the standard deviation of the gaussian curve
#     a: the factor on the gaussian curve that determines the height of the curve
#     x_part: the list of x-locations in mv-ns which were passed to each gaussian fit to determine the curve.
def gauss_estimate(import_data_results, peak_results, gauss_width=10):
  #error testing
  if gauss_width<=0 or not isinstance(gauss_width,int):
    raise Exception("gauss_width must be an integer greater than 0, current value is ",gauss_width)
    
  #import data
  area=import_data_results["area"]
  h=import_data_results["h"]
  axis=h.axes[0]
  amax=axis.edges[-1]
  amin=axis.edges[0]
  bin_centers=axis.centers
  nbins=len(bin_centers)
  bin_width=(axis.edges[-1]-axis.edges[0])/nbins
  n, _= h.to_numpy()
    
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
#- fig, ax are the figure and axis respectively of the plot so the user may make further edits to the plot
def plot_gauss_estimate(import_data_results,gauss_dict):
  #import data
  h=import_data_results["h"]
  
  #plot regular data
  fig,ax = plot.make_simple_figure() 
  plot.plot_data1d(ax=ax, data=h, label='Data', histtype='fill')  
  
  #plot gaussians
  for idpeak, peak in enumerate(gauss_dict["peak"]):
    ax.plot(gauss_dict["x_part"][idpeak], gauss(gauss_dict["x_part"][idpeak],gauss_dict["a"][idpeak],gauss_dict["mu"][idpeak],gauss_dict["sigma"][idpeak]), label='Fit of Peak at '+str(int(peak)))
  plot.add_std_label(ax=ax, label='Preliminary', rlabel='Gaussian Estimation')
  ax.set_xlabel('Readout [mV-ns]')
  ax.set_ylabel('Number of events')
  ax.legend()
    
  return fig, ax

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

#- This funciton ensures that any upper and lower bounds passed to zfit are reasonable
#- variable_estimates is the dictionary of estimates for each variable with the key as the variable name
#- limits_dict is a user set dictionary where each key is the name of each variable:
#   - The content of each element of the dictionary is another dictionary which has "width": the distance from the estimation the bounds should be, and the optional values of "upper_max" and "lower_max" which provide the logical limits which a variable value may not cross.
#- returns limits_dict where the keys are the names of each of the variables, and the value is a dictionary:
#     width: the distance from the estimation the upper and lower bounds should be
#     upper_max: the maximum value allowed by logic for a variable
#     lower_max: the minimum value allowed by logic for a variable
#     upper_bound: the upper bound passed to zfit to try while fitting
#     lower_bound: the lower bound passed to zfit to try while fitting
def set_bounds(variable_estimates,limits_dict):
  for key, value in variable_estimates.items():
    #error testing
    if key not in limits_dict:
      raise Exception("The variable ",key,"is not in the limits_dict")
    if "width" not in limits_dict[key]:
      raise Exception("The width is not set in limits_dict for the variable ",key)
    if limits_dict[key]["width"] <=0:
      raise Exception("width <= 0 in limits_dict for the variable ",key)
    
    #calculate correct bounds
    lower_bound=value-limits_dict[key]["width"]
    upper_bound=value+limits_dict[key]["width"]
    if "lower_max" in limits_dict[key]:
      if lower_bound < limits_dict[key]["lower_max"]:
        lower_bound= limits_dict[key]["lower_max"]
    if "upper_max" in limits_dict[key]:
      if upper_bound > limits_dict[key]["upper_max"]:
          upper_bound=limits_dict[key]["upper_max"]
    limits_dict[key]["upper_bound"]=upper_bound
    limits_dict[key]["lower_bound"]=lower_bound
  
  return limits_dict

#- This function takes the pdf and runs an iterative pdf fit to ensure no variables hit the upper or lower bounds
#- pdf is the zfit probability distribution function
#- parameters is a dictionary of the zfit parameters with their names as the key and the parameters as the values
#- max_iterations is an integer indicating the maximum number of iterations allowed during the fitting
#- limits dict is the limits dictionary created by the set_bounds function
#- import_data_results is the output of the function import_data
#- OPTIONAL: message is an optional bool usually set to false which can give messages relating to the final state of the fit
#- returns zfit result and zfit pdf
def run_iterative_pdf_fit(pdf,parameters,obs,max_iterations,limits_dict,import_data_results,message=False):
  #error testing
  if max_iterations <=0 or not isinstance(max_iterations,int):
    raise Exception("max_iterations must be a positive integer")
  for key in parameters:
    if key not in limits_dict:
      raise Exception("The parameter ",key,"is not in the limits_dict, ensure the limits are set properly")
    if "width" not in limits_dict[key]:
      raise Exception("The width is not set in limits_dict for the variable ",key)
    if limits_dict[key]["width"] <=0:
      raise Exception("width <= 0 in limits_dict for the variable ",key)
    if limits_dict[key]["lower_bound"]>limits_dict[key]["upper_bound"]:
      raise Exception("Illogical bounds for ",key," upper_bound is ",limits_dict[key]["upper_bound"]," lower_bound is ",limits_dict[key]["lower_bound"])
    
  #set up pdf
  binning = zfit.binned.RegularBinning(400, -200, 1500, name="x")
  obs_bin = zfit.Space("x", binning=binning)
  data_unbinned = zfit.Data.from_numpy(obs=obs, array=np.array(import_data_results["area"]))
  data_bin = data_unbinned.to_binned(obs_bin) 
  
  #iterate to run pdf and then determine if it should be rerun and set the new upper and lower bounds
  run_fitting=False
  at_logical_limit=[]
  for i in range(max_iterations):
    run_fitting=False
    pdf_bin = zfit.pdf.BinnedFromUnbinnedPDF(pdf, obs_bin)
    nll_bin = zfit.loss.BinnedNLL(pdf_bin, data_bin)
    minimizer = zfit.minimize.Minuit()
    result = minimizer.minimize(nll_bin)
    result.hesse()
    
    #Determine if the last run is a good fit and don't run extra unnecessary code and make output statements for each
    if i == max_iterations-1:
      if message:
        non_logical_limit=False
        for name,parameter in parameters.items():
          if parameter.at_limit and name not in at_logical_limit:
            if non_logical_limit == False:
              print("In ",max_iterations," iterations the pdf has not converged properly, the following parameters hit limits which are not logically necessary")
              non_logical_limit=True
            print("parameter: "+str(name)+" value: "+str(result.params[parameter]["value"])+" upper_bound: "+str(limits_dict[name]["upper_bound"])+" lower_bound: "+str(limits_dict[name]["lower_bound"]))
      break
    
    at_logical_limit=[]
    
    #loop through parameters to test if any of them hit a limit, and if so expand the bounds as reasonable
    for name,parameter in parameters.items():
      if parameter.at_limit:
        value=result.params[parameter]["value"]
        error=result.params[parameter]["hesse"]["error"]
        upper_error=value+error
        lower_error=value-error
        
        #check upper bounds
        if limits_dict[name]["upper_bound"]-upper_error<=10e-4:
          test_upper_limit=limits_dict[name]["upper_bound"]+limits_dict[name]["width"]
          if "upper_max" not in limits_dict[name]:
            run_fitting=True
            limits_dict[name]["upper_bound"]=test_upper_limit
            parameter.upper=limits_dict[name]["upper_bound"]
          else:
            if upper_error < limits_dict[name]["upper_max"]:
              run_fitting=True
              if test_upper_limit>limits_dict[name]["upper_max"]:
                limits_dict[name]["upper_bound"]=limits_dict[name]["upper_max"]
                parameter.upper=limits_dict[name]["upper_bound"]
              else:
                limits_dict[name]["upper_bound"]=test_upper_limit
                parameter.upper=limits_dict[name]["upper_bound"]
            else:
              at_logical_limit.append(name)
    
        #check lower bounds
        if lower_error-limits_dict[name]["lower_bound"]<=10e-4:
          test_lower_limit=limits_dict[name]["lower_bound"]-limits_dict[name]["width"]
          if "lower_max" not in limits_dict[name]:
            run_fitting=True
            limits_dict[name]["lower_bound"]=test_lower_limit
            parameter.lower=limits_dict[name]["lower_bound"]
          else:
            if lower_error > limits_dict[name]["lower_max"]:
              run_fitting=True
              if test_lower_limit<limits_dict[name]["lower_max"]:
                limits_dict[name]["lower_bound"]=limits_dict[name]["lower_max"]
                parameter.lower=limits_dict[name]["lower_bound"]
              else:
                limits_dict[name]["lower_bound"]=test_lower_limit
                parameter.lower=limits_dict[name]["lower_bound"]
            else:
              at_logical_limit.append(name)
    
    #if no parameters hit a limit, or only hit limits that are logical limits, do not iterate again
    if run_fitting==False:
      break
  
  #at end of run message if any variables hit a logical limit
  if len(at_logical_limit)>0 and message:
        print("The following parameters reached a logical limit ")
        for name in at_logical_limit:
          print("parameter: "+str(name)+" value: "+str(result.params[parameters[name]]["value"])+" upper_bound: "+str(limits_dict[name]["upper_bound"])+" lower_bound: "+str(limits_dict[name]["lower_bound"]))  

  return result, pdf
  
