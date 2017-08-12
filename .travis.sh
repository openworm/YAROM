#!/bin/sh -ex

pip install --upgrade 'setuptools' 'six>=1.9'
pip install -r requirements.txt
if [ $DEPLOY ] ; then
    sudo apt-get install ruby
    pip install twine
    gem install travis
else
    if [ $INFERENCE ] ; then
        pip install -r inference.requirements.txt
    fi
    if [ $ZODB ] ; then
        pip install -r zodb.requirements.txt
    fi
    python setup.py develop
fi
