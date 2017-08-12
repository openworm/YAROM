#!/bin/bash -e

while read DOWNSTREAM_REPO DOWNSTREAM_BRANCH ; do
    echo "Attempting to trigger dowstream Travis-CI build of $DOWNSTREAM_REPO for branch $DOWNSTREAM_BRANCH"
    body='{
    "request": {
    "branch":"'$DOWNSTREAM_BRANCH'"
    }}'

    repo=${DOWNSTREAM_REPO//\//%2f}
    curl -s -X POST \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -H "Travis-API-Version: 3" \
       -H "Authorization: token $TRAVIS_API_TOKEN" \
       -d "$body" \
       "https://api.travis-ci.org/repo/$repo/requests"
done < ./downstream-builds.txt
