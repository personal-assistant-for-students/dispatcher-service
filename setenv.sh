#!/bin/bash

# Define
# name and dir of env
export ENV_NAME="urfu"
export DIR="$(pwd)/$ENV_NAME" # Check that you are in right directory
# encoding
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
# Create env if it isn't exist
if [ ! -d "$DIR" ]; then
    python3 -m virtualenv "$ENV_NAME"
fi
# Set current env
source "$DIR/bin/activate"
# Set dependencies
pip install -r requirements.txt
# Check current dependencies
pip freeze
echo "Virtual environment $ENV_NAME is set and active."