#!/usr/bin/env bash

set -e
set -x

mypy uplid tests.py
ruff uplid tests.py
ruff format uplid tests.py --check