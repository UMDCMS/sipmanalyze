"""

convert_waveform_txt_to_parquet.py

Simple file for converting the .txt wavefile to the standard root format.

"""
import sipmanalyze.formats as forms
import argparse
import os
import awkward

if __name__ == "__main__":
  parser = argparse.ArgumentParser(
    "Converting a waveform file to a standard root file format.")
  parser.add_argument('input', type=str, nargs='+', help='input .txt file')
  args = parser.parse_args()
  for idx, in_f in enumerate(args.input):
    try:
      out_f = in_f.replace('.txt', '.root')
      print(f'Converting file {in_f} [{idx+1}/{len(args.input)}]')
      std_cont = forms.standard.standard_container.from_txt(in_f)
      std_cont.data['lumival'] = std_cont.data.payload[:, 0]
      std_cont.data['uncval'] = std_cont.data.payload[:, 1]
      std_cont.data = awkward.zip(
        {f: std_cont.data[f]
         for f in std_cont.data.fields
         if f != 'payload'})

      std_cont.save_to_file(out_f)
      del std_cont
    except Exception as err:
      print(err)
      pass
