#!/bin/sh

BRANCH=${TRAVIS_BRANCH:-$(git symbolic-ref --short HEAD)}
ENV=travis-ci
COMMIT=$(git rev-parse HEAD)
OWCS_USERNAME=travisci-yarom
echo "Branch: $BRANCH"
echo "Environment: $ENV"
echo "Commit: $COMMIT"
echo "User: $OWCS_USERNAME"

py.test $@ --code-speed-submit="https://owcs.pythonanywhere.com/" \
    --environment="$ENV" --branch="$BRANCH" --commit="$COMMIT" \
    --project=YAROM --password=${OWCS_KEY} --username=$OWCS_USERNAME \
    ./tests/ProfileTest.py
