#!/bin/sh -ex
echo "$TRAVIS_COMMIT_MESSAGE" | head -n1 | grep -q '^MINOR:' && exit 0
if [ $DEPLOY ] ; then
    HEAD_REV=$(git rev-parse HEAD)
    ORIGIN_DEV_REV=$(git rev-parse origin/dev)
    if [ "$HEAD_REV" != $ORIGIN_DEV_REV ] ; then
        echo "Not deploying since we aren't on the 'dev' branch" >&2
        exit 0
    fi
    ./check-build-status.sh
    ./deploy.sh
    ./travis-downstream-trigger.sh
else
    ./codespeed-submit.sh
fi
