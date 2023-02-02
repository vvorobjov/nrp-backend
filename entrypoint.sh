#!/bin/bash

sudo nginx
uwsgi --ini /usr/uwsgi-nrp.ini --plugin python3 --pyargv "--verbose"
