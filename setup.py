# -*- coding: utf-8 -*-

from setuptools import setup
import sys

with open('requirements.txt') as f:
    required = f.read().splitlines()

import os

long_description = open("README.md").read()

setup(
    name = "YAROM",
    install_requires=required,
    dependency_links=[
        "git://github.com/NeuralEnsemble/libNeuroML.git#egg=libNeuroML",
        "git://github.com/zopefoundation/ZODB.git#egg=ZODB",
        ],
    setup_requires="six==1.7.3",
    version = '0.5.0-alpha',
    packages = ['yarom'],
    package_data = {"yarom":['default.conf']},
    author = "Mark Watts",
    author_email = "mark.watts2015@gmail.com",
    description = "Yet Another RDF-Object Mapper",
    long_description = long_description,
    license = "BSD",
    url="http://PyOpenWorm.readthedocs.org/en/latest/",
    download_url = 'https://github.com/mwatts15/YAROM/archive/master.zip',
    classifiers = [
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering']
)
