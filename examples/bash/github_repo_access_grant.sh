#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

export PYTHONPATH=$SCRIPT_DIR/..

python classroom_utils/main.py github repo access grant --repo classroom-utils-example-org/excercise_description --permission pull