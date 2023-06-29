"""

convert_waveform_txt_to_parquet.py

Simple file for converting the .txt wavefile to the standard root format.

"""
import sipmanalyze.formats as forms
import argparse
import awkward
import os

std_cont = forms.standard.standard_container.from_txt('lowlight_testing.txt')

std_cont.data = awkward.zip({
  **{
    f: std_cont.data[f]
    for f in std_cont.data.fields if f != 'payload'
  },  #
  'readout': std_cont.data.payload,
})
print(std_cont.data.time.__repr__)
print(std_cont.data.readout)
print(std_cont.data.fields)
std_cont = forms.standard.standard_container.from_root('root_format_test.root')
print(std_cont.data.time.__repr__)

print(std_cont.data.fields)
std_cont = forms.standard.standard_container.from_root(
  'lowlightcollect_root_test.root')
print(std_cont.data.time.__repr__)
print(std_cont.data.fields)

