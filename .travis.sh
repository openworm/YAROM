#!/bin/sh

echo pip install -r requirements.txt
pip install -r requirements.txt
if [ $INFERENCE ] ; then
   echo pip install -r inference.requirements.txt
   pip install -r inference.requirements.txt

fi
if [ $ZODB ] ; then
   echo pip install -r zodb.requirements.txt
   pip install -r zodb.requirements.txt
fi

python setup.py develop
