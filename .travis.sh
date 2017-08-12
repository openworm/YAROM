#!/bin/sh -ex

pip install --upgrade 'setuptools' 'six>=1.9'
pip install -r requirements.txt
if [ $DEPLOY ] ; then
    apt-get install ruby
    pip install twine
    gem install travis
else
    if [ $INFERENCE ] ; then
        echo pip install -r inference.requirements.txt
        pip install -r inference.requirements.txt

    fi
    if [ $ZODB ] ; then
        echo pip install -r zodb.requirements.txt
        pip install -r zodb.requirements.txt
    fi

    python setup.py develop
fi
