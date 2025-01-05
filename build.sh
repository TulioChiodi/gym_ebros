#!/usr/bin/env bash
# exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate --fake workouts zero  # First, fake revert workouts migrations
python manage.py migrate --fake-initial  # Then fake initial migration
python manage.py migrate  # Finally, apply remaining migrations 