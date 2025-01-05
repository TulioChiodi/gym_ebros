#!/usr/bin/env bash
# exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Drop and recreate the database tables
python manage.py dbshell << EOF
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
EOF

# Apply migrations
python manage.py migrate 