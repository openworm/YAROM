#!/bin/sh -e

while read DOWNSTREAM_REPO DOWNSTREAM_BRANCH ; do
    body='{
    "request": {
    "branch":"'$DOWNSTREAM_BRANCH'"
    }}'

    curl -s -X POST \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -H "Travis-API-Version: 3" \
       -H "Authorization: token $TRAVIS_API_TOKEN" \
       -d "$body" \
       "https://api.travis-ci.org/repo/${DOWNSTREAM_REPO//\//%2f}/requests" 2>&1 > /dev/null
done < ./downstream-builds.txt
