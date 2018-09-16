#!/bin/bash -xe

date=$(date +"%Y%m%d%H%M%S")
sed -i -r "s/__version__ = '([^']+)\\.post0'/__version__ = '\\1.post$date'/" yarom/__init__.py
sed -i -r "s/^(.*)\\.post0/\\1.post$date/" version.txt
python setup.py egg_info sdist
twine upload -c "Built by travis-ci. Uploaded after $(date +"%Y-%m-%d %H:%M:%S")" dist/YAROM*tar.gz
