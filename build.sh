#!/usr/bin/env bash
# exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Only reset database if RESET_DATABASE is set to "true"
if [ "$RESET_DATABASE" = "true" ]; then
    echo "Resetting database..."
    python manage.py dbshell << EOF
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
EOF
fi

# Apply migrations
python manage.py migrate 