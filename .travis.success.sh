#!/bin/sh -ex
echo "$TRAVIS_COMMIT_MESSAGE" | head -n1 | grep -q '^MINOR:' && exit 0
if [ $DEPLOY ] ; then
    if [ "$TRAVIS_BRANCH" ] ; then
        if [ "$TRAVIS_BRANCH" != dev ] ; then
            echo "Not deploying since Travis-CI says we aren't on the 'dev' branch" >&2
            exit 0
        fi
    else
        BRANCH=$(git for-each-ref --format='%(objectname) %(refname:short)' refs/heads \
                 | awk "/^$(git rev-parse HEAD)/ {print \$2}" \
                 | grep dev)
        if [ "$BRANCH" = 'dev' ] ; then
            echo "Not deploying since we aren't on the 'dev' branch" >&2
            exit 0
        fi
    fi
    ./check-build-status.sh
    ./deploy.sh
    ./travis-downstream-trigger.sh
else
    ./codespeed-submit.sh
fi
