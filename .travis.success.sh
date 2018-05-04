#!/bin/sh -ex
echo "$TRAVIS_COMMIT_MESSAGE" | head -n1 | grep -q '^MINOR:' && exit 0
if [ $DEPLOY ] ; then
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [ $current_branch == 'dev' ] ; then
        ./check-build-status.sh
        ./deploy.sh
        ./travis-downstream-trigger.sh
    fi
else
    ./codespeed-submit.sh
fi
