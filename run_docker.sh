#!/bin/bash

bugfix_commits_file=$1
conf_file=$2
repos_dir=$3
iteration_number=$4
date_filter=$5

echo +++ PARAMS +++
echo bugfix_commits_file=$bugfix_commits_file
echo conf_file=$conf_file
echo repos_dir=$repos_dir
echo iteration_number=$iteration_number
echo date_filter=$date_filter


docker build -t pyszz .
mkdir -p out

# replace with `docker run -d` to run the container in detached mode
docker run \
        -v $PWD/out:/usr/src/app/out \
        -v $(pwd)/$bugfix_commits_file:/usr/src/app/bugfix_commits.json \
        -v $(pwd)/$conf_file:/usr/src/app/conf.yml \
        -v $(pwd)/$repos_dir:/usr/src/app/cloned \
        pyszz bugfix_commits.json conf.yml cloned/ $iteration_number $date_filter
