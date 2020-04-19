# Cloudsnap Analytics

[![Build Status](https://travis-ci.com/mozilla-it/cloudsnap-analytics.svg?token=tcy8Sk3pbmSki6yTjsma&branch=master)](https://travis-ci.com/mozilla-it/cloudsnap-analytics)

## Development

1. `python3 -m venv venv`
2. `source venv/bin/activate`
3. `pip3 install -r requirements.txt`
4. `python3 site/app/__init__.py`

## Installer

### Installer Creation (Linux)

1. `cd site`
2. `pyinstaller --onefile --add-data 'app/templates:app/templates' --add-data 'app/static:app/static' __init__.py`

### Installer Creation (OSX)

1. `python setup.py py2app`

## Author(s)

Stewart Henderson <shenderson@mozilla.com>
