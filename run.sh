#!/bin/bash

echo "Starting locally task manager application"

source set_virtualenv.sh
sh set_env.env
docker-compose up &
pytest

python3  src/dispatcher_app.py

# Deactivation is not strictly necessary for a script, as the environment changes
# do not persist when the script finishes
echo "Script execution finished."
