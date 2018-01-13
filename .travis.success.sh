#!/bin/sh -e
echo "$TRAVIS_COMMIT_MESSAGE" | head -n1 | grep -q '^MINOR:' && exit 0
./codespeed-submit.sh
if [ $DEPLOY ] ; then
    ./check-build-status.sh && ./deploy.sh && ./travis-downstream-trigger.sh
fi
