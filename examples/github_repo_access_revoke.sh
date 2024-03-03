#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

export PYTHONPATH=$SCRIPT_DIR/..

python classroom_utils/main.py github repo access revoke --repo classroom-utils-example-org/excercise_description --class-name example_class_a