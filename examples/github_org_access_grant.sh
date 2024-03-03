#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

export PYTHONPATH=$SCRIPT_DIR/..

python classroom_utils/main.py github org access grant --org-name classroom-utils-example-org --class-name example_class_a