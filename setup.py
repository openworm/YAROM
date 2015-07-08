# -*- coding: utf-8 -*-

from setuptools import setup
import sys
import os

with open('requirements.txt') as f:
    required = f.read().splitlines()
    on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
    if on_rtd:
        required.append("numpydoc")

import os

long_description = open("README.rst").read()

setup(
    name = "YAROM",
    install_requires=required,
    dependency_links=[
        "git://github.com/NeuralEnsemble/libNeuroML.git#egg=libNeuroML",
        "git://github.com/zopefoundation/ZODB.git#egg=ZODB",
        "git://github.com/RDFLib/FuXi.git#egg=FuXi",
        ],
    setup_requires="six==1.7.3",
    version = '0.6.0',
    packages = ['yarom'],
    package_data = {"yarom":['default.conf', 'rules.n3']},
    author = "Mark Watts",
    author_email = "wattsmark2015@gmail.com",
    description = "Yet Another RDF-Object Mapper",
    long_description = long_description,
    license = "BSD",
    url="http://yarom.readthedocs.org/en/latest/",
    download_url = 'https://github.com/mwatts15/YAROM/archive/master.zip',
    classifiers = [
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering'],
    zip_safe = False
)
