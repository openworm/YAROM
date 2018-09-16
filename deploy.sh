#!/bin/bash -xe

sed -i -r "s/__version__ = '([^']+).post0'/__version__ = '\\1.post$(date +"%Y%m%d%H%M%S")'/" yarom/__init__.py
python setup.py egg_info sdist
twine upload -c "Built by travis-ci. Uploaded after $(date +"%Y-%m-%d %H:%M:%S")" dist/YAROM*tar.gz
