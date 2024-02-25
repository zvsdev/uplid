#!/usr/bin/env bash

set -e
set -x

mypy lpid tests.py
ruff lpid tests.py
ruff format lpid tests.py --check