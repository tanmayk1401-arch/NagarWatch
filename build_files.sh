#!/bin/bash
python -m pip install -r requirements.txt
python backend/manage.py collectstatic --noinput

