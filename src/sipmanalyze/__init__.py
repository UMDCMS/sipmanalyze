from . import version

__version__ = version.__version__

import sys

if sys.version_info.major < 3:
  import warnings

  warnings.warn("coffea only supports python3 as of 1 January 2020!")
  warnings.warn(
    "If you are using python2 and run into problems please submit a pull request to fix the issue!"
  )
