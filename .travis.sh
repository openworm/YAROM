#!/bin/sh

pip install -r requirements.txt
if [ $INFERENCE ] ; then
   pip install -r inference.requirements.txt
fi
if [ $ZODB ] ; then
   pip install -r zodb.requirements.txt
fi

