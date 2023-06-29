"""

convert_waveform_txt_to_parquet.py

Simple file for converting the .txt wavefile to the standard root format.

"""
import sipmanalyze.formats as forms
import argparse
import os

if __name__ == "__main__":
  parser = argparse.ArgumentParser(
    "Converting a waveform file to a standard root file format.")
  parser.add_argument('input', type=str, nargs='+', help='input .txt file')
  args = parser.parse_args()
  for idx, in_f in enumerate(args.input):
    try:
      out_f = in_f.replace('.txt', '.root')
      print(f'Converting file {in_f} [{idx+1}/{len(args.input)}]')
      container = forms.waveform.waveform_container.from_txt(in_f)
      container.save_to_file(out_f)
      del container
    except Exception as err:
      print(err)
      pass