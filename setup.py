from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="zyte-api",
    version="0.6.0",
    description="Python interface to Zyte API",
    long_description=Path("README.rst").read_text(encoding="utf-8"),
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
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
