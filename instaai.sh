#!/bin/bash
# InstaAI Studio - Unix/Linux/macOS Script
# This makes it easier to run the CLI on Unix-like systems

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/src"
python main.py "$@"
