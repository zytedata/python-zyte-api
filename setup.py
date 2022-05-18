#!/usr/bin/env python
import os
from setuptools import setup, find_packages


def get_version():
    about = {}
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, 'zyte_api/__version__.py')) as f:
        exec(f.read(), about)
    return about['__version__']


setup(
    name='zyte-api',
    version=get_version(),
    description='Python interface to Zyte Data API',
    long_description=open('README.rst').read() + "\n\n" + open('CHANGES.rst').read(),
    long_description_content_type='text/x-rst',
    author='Zyte Group Ltd',
    author_email='opensource@zyte.com',
    url='https://github.com/zytedata/python-zyte-api',
    packages=find_packages(exclude=['tests', 'examples']),
    entry_points = {
        'console_scripts': ['zyte-api=zyte_api.__main__:_main'],
    },
    install_requires=[
        'requests',
        'tenacity',
        'aiohttp >= 3.6.0',
        'tqdm',
        'attrs',
        'runstats',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
