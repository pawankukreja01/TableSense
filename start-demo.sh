#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py seed_demo
echo 'Open http://127.0.0.1:8080 in your browser.'
exec .venv/bin/python manage.py runserver 127.0.0.1:8080 --noreload
