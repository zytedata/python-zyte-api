#!/usr/bin/env python
import os

from setuptools import find_packages, setup


def get_version():
    about = {}
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, "zyte_api/__version__.py")) as f:
        exec(f.read(), about)
    return about["__version__"]


setup(
    name="zyte-api",
    version=get_version(),
    description="Python interface to Zyte API",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    author="Zyte Group Ltd",
    author_email="opensource@zyte.com",
    url="https://github.com/zytedata/python-zyte-api",
    packages=find_packages(exclude=["tests", "examples"]),
    entry_points={
        "console_scripts": ["zyte-api=zyte_api.__main__:_main"],
    },
    install_requires=[
        "aiohttp >= 3.8.0",
        "attrs",
        "brotli",
        "runstats",
        "tenacity",
        "tqdm",
        "w3lib >= 2.1.1",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
