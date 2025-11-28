import os
from importlib.metadata import version, PackageNotFoundError
import tomllib

try:
    __version__ = version("microtexture")
except PackageNotFoundError:
    try:
        toml = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../pyproject.toml')
        __version__ = tomllib.load(open(toml, "rb"))["project"]["version"]
    except:
        __version__ = "NA"
