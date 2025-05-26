#!/usr/bin/env bash
# Exit on error
set -o errexit

# Update package lists and install necessary build tools
sudo apt-get update
sudo apt-get install -y build-essential python3-dev

# Upgrade pip and setuptools
pip install --upgrade pip setuptools

# Install project dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate
