"""

formats

Containers for the various data files. The containers typically consist of data
members:

- A dictionary with of readout settings
- A awkward array of the unmodified data.

Along with various helper function to process the unmodified data into something
that can be used by for analysis level code.

"""

from . import waveform
from . import standard