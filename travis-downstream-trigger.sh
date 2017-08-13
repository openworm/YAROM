#!/bin/bash -e

LAST_CACHE=0
CACHE_INTERVAL=2
CACHED_TRAVIS_JOBS=$(mktemp)

get_cached_travis_jobs () {
    NOW=$(date +"%s")
    if [ $(( NOW - LAST_CACHE )) -ge $CACHE_INTERVAL ] ; then
        travis show $TRAVIS_BUILD_NUMBER --no-interactive \
            | grep "^#$TRAVIS_BUILD_NUMBER" \
            | grep -v DEPLOY=1 > $CACHED_TRAVIS_JOBS
        LAST_CACHE=$(date +"%s")
    fi
    cat $CACHED_TRAVIS_JOBS
}

get_passed_jobs () {
    get_cached_travis_jobs | grep passed | wc -l
}

get_failed_jobs () {
    get_cached_travis_jobs | egrep 'fail|error|cancel' | wc -l
}

get_total_jobs () {
    get_cached_travis_jobs | wc -l
}

if [ $DEPLOY ] ; then
    total_jobs=$(get_total_jobs)
    passed_jobs=$(get_passed_jobs)
    failed_jobs=$(get_failed_jobs)
    echo 'Waiting for other jobs to finish ...'
    while [ $failed_jobs -lt 1 -a $total_jobs -ne $passed_jobs ] ; do
        sleep 10
        echo .
        passed_jobs=$(get_passed_jobs)
        failed_jobs=$(get_failed_jobs)
    done

    if [ $total_jobs -ne $passed_jobs ] ; then
        echo "One or more jobs failed. Not triggering downstream builds"
        exit
    fi

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
