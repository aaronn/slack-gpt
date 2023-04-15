#!/usr/bin/env bash

set -euxo pipefail

source setup-poetry.sh

poetry run python slackgpt.py
