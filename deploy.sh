#!/bin/bash -xe

python setup.py egg_info --tag-build=--post$(date +"%Y%m%d%H%M%S") sdist
twine upload -c "Built by travis-ci. Uploaded after $(date +"%Y-%m-%d %H:%M:%S")" dist/YAROM*tar.gz
