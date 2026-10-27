"""stario-create: scaffold and grow Stario apps."""

from importlib.metadata import version as _version

from stario_create.data import data_dir as data_dir

__version__ = _version("stario-create")

# The Stario major this release tracks. Templates and the guide target it.
TRACKS_STARIO = "5"
