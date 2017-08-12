#!/bin/bash -e

get_passed_jobs () {
    travis show $TRAVIS_BUILD_NUMBER --no-interactive \
        | grep "^#$TRAVIS_BUILD_NUMBER" \
        | grep -v DEPLOY=1 | grep passed | wc -l
}

get_total_jobs () {
    travis show $TRAVIS_BUILD_NUMBER --no-interactive \
        | grep "^#$TRAVIS_BUILD_NUMBER" \
        | grep -v DEPLOY=1 | wc -l
}

if [ $DEPLOY ] ; then
    total_jobs=$(get_total_jobs)
    passed_jobs=$(get_passed_jobs)
    while [ $total_jobs -ne $passed_jobs ] ; do
        sleep 10
        passed_jobs=$(get_passed_jobs)
    done

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
fi
