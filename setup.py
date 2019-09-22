# -*- coding: utf-8 -*-

from setuptools import setup
import os
import sys
from glob import glob

REQUIRED = []
with open('requirements.txt') as f:
    REQUIRED = f.read().splitlines()
    on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
    if on_rtd:
        REQUIRED.append("numpydoc")
FEATURE_DEPS = {}

PY2 = sys.version_info.major == 2

for feature_file in glob("*.requirements.txt"):
    feature, _ = feature_file.split(".", 1)

    with open(feature_file) as f:
        FEATURE_DEPS[feature] = f.read().splitlines()

VERSION = open("version.txt").read().strip()
LONG_DESCRIPTION = open("README.rst").read()

setup(
    name="YAROM",
    setup_requires=['six>=1.9.0'],
    tests_require=[] + (['mock==2.0.0'] if PY2 else []),
    install_requires=REQUIRED,
    dependency_links=[
        "git://github.com/zopefoundation/ZODB.git#egg=ZODB",
        "git://github.com/RDFLib/rdflib-zodb.git#egg=rdflib_zodb-1.0.0",
    ],
    version=VERSION,
    packages=['yarom'],
    package_data={"yarom": ['default.conf', 'rules.n3']},
    author="Mark Watts",
    author_email="wattsmark2015@gmail.com",
    description="Yet Another RDF-Object Mapper",
    long_description=LONG_DESCRIPTION,
    license="BSD 3-clause",
    url="http://yarom.readthedocs.org/en/latest/",
    download_url='https://github.com/mwatts15/YAROM/archive/v'+VERSION+'.tar.gz',
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Scientific/Engineering'],
    extras_require=FEATURE_DEPS,
    zip_safe=False
)
