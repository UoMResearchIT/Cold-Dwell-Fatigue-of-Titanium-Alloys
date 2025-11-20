from importlib.metadata import version, PackageNotFoundError
import tomllib

try:
    __version__ = version("microtexture")
except PackageNotFoundError:
    try:
        __version__ = tomllib.load(open("pyproject.toml", "rb"))["project"]["version"]
    except:
        pass
