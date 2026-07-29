#!/usr/bin/env bash
# Exit on error
set -o errexit


# Modify this line as needed for your package manager (pip, poetry, etc.)
pip install -r requirements.txt


# Convert static asset files
python manage.py collectstatic --no-input


# Apply any outstanding database migrations
python manage.py migrate


# Seed database with demo data
python manage.py seed_data


# Create test user
python manage.py create_test_user