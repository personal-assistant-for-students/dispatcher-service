#!/bin/bash

echo "Starting locally task manager application"

while true; do
    read -p "Continue with tests? yes/no: " yn
    case $yn in
        [Yy]* )
            # Source the environment setup script
            source ./setenv.sh

            # Run unit tests using unittest discover
            echo "Running unit tests..."
            cd test || exit
            python -m unittest discover -s test -p "unit_tests_*.py"
            cd ..

            # Check if all tests passed
            if [ $? -eq 0 ]; then
                echo "All unit tests passed. Starting the application..."
                # Run the main Python script
                python3  src/dispatcher_app.py

            else
                echo "Unit tests failed. Exiting..."
                exit 1
            fi
            break;;
        [Nn]* ) exit;;
        * ) echo "Please, answer yes or no.";;
    esac
done

# Deactivation is not strictly necessary for a script, as the environment changes
# do not persist when the script finishes
echo "Script execution finished."
