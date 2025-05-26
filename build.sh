#!/usr/bin/env bash
# Exit on error
set -o errexit

sudo apt-get update
sudo apt-get install -y build-essential python3-dev
pip install --upgrade pip setuptools

# Modify this line as needed for your package manager (pip, poetry, etc.)
pip install -r requirements.txt

# Convert static asset files
python manage.py collectstatic --no-input

# Apply any outstanding database migrations
python manage.py migrate
