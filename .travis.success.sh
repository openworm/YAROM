#!/bin/sh
echo "$TRAVIS_COMMIT_MESSAGE" | head -n1 | grep '^MINOR:' >/dev/null
if [ $? -ne 0 ] ; then
    ./codespeed-submit.sh
    ./deploy.sh && ./travis-downstream-trigger.sh
fi
