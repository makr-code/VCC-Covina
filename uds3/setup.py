from setuptools import setup
from glob import glob

# Simple editable-install helper. It installs all top-level .py modules
# so the environment can import the project's modules consistently.
py_modules = [p[:-3] for p in glob("*.py") if p.endswith(".py") and p != "setup.py"]

setup(
    name="uds3",
    version="0.0.0",
    description="UDS3 helpers (editable install for local dev)",
    py_modules=py_modules,
    include_package_data=True,
)
