#!/usr/bin/env python
"""nosh.py - Eat a little data, using Splunk.

Features
========
    nosh.py uploads a local file to a remote Splunk server and opens a web
    browser to the Splunk web interface, allowing you to search the contents
    of your file, report on contents within the file, and more.

Installation
============
    1. Open nosh.py in your favorite $EDITOR and set splunk_server, username and
    password.
    2. Fix nosh.py permissions: chmod +x nosh.py
    3. Copy nosh.py to a directory in your $PATH

Usage
=====
    nosh.py takes one argument: The name of a file to consume.

    For example, to consume your /var/log/messages log file with Splunk:
        $ nosh.py /var/log/messages

    ..which will return:
        Uploading /var/log/messages...
        Waiting 5 seconds for Splunk to index the file.
        About to open a this URL in a browser: http://splunk.example.com:8000/...?q=search%20source%3D%22messages%22

    ..and open a web browser to the Splunk web interface.

MacOS X Service
===============
    nosh.py can be configured as a Mac OS X Service. When enabled, you can use
    Mac OS X contextual menus to select and index files using Splunk.

    To create a custom Mac OS X Service for nosh.py:
        1. Open Automator.app
        2. When prompted for a template, select 'Service' (or go to File -> New).
        3. Set 'Service receives selected' to 'files or folders' in
        'any application'.
        4. In your Actions Library select 'Run Shell Script'.
        5. In the 'Run Shell Script' action set 'Pass input:' to 'as arguments'.
        6. For the acutal shell script to run, enter: /path/to/nosh.py $*
        7. File -> Save and set 'Save Service as:' to 'Index with Splunk'.

Meta
====
    Author: Greg Albrecht (gba@splunk.com)
    Version: $Id: //splunk/qa/nosh/nosh.py#6 $
    Copyright: Copyright 2012 Greg Albrecht
    License: Free.
"""
## Change Me!   <----- CHANGE STUFF HERE <------ HEY LOOK AT ME
splunk_server = 'localhost'
username = 'admin'
password = 'changeme'

import httplib
import logging
import logging.handlers
import os
import urllib
import socket
import sys
import time

from xml.dom import minidom

## Probably nothing to change here.
# default_host sets the 'host' field to associate with uploaded data.
# Defaults to your hostname.
default_host = socket.gethostname()
splunk_server_mgmt_port = '8089'
splunk_server_http_port = '8000'

## Definitely nothing to change here.
__author__ = 'Greg Albrecht <gba@splunk.com>'
__version__ = '$Id: //splunk/qa/nosh/nosh.py#6 $'
mgmt_host_port = ':'.join((splunk_server, splunk_server_mgmt_port))
params = {'host': default_host}
logger = logging.getLogger('nosh')
cli_logger = logging.StreamHandler()
cli_logger_format = logging.Formatter('%(levelname)s - %(message)s')
logger.setLevel(logging.INFO)
cli_logger.setLevel(logging.INFO)
cli_logger.setFormatter(cli_logger_format)
logger.addHandler(cli_logger)


def show_results(search_url):
    try:
        import webbrowser
        logger.info("About to open a this URL in a browser: %s" % search_url)
        webbrowser.open(search_url)
    except:
        logger.info("Have at it: %s" % search_url)


def get_session_key(mgmt_host_port, username, password):
    http_conn = httplib.HTTPSConnection(mgmt_host_port)
    http_conn.request(
        method='POST', url='/services/auth/login', headers={},
        body=urllib.urlencode({'username': username, 'password': password}))
    server_response = http_conn.getresponse()
    if not server_response.status == 200:
        logger.error(
            "Server did not return 200 (it returned '%s %s'). "
            "Perhaps you didn't set your password?"
            % (server_response.status, server_response.reason))
        raise Exception(server_response.status, server_response.reason)
    response_content = server_response.read()
    return minidom.parseString(response_content).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue


def rest_build_endpoint(params):
    endpoint = '/services/receivers/stream'
    if params:
        endpoint += '?' + '&'.join(["%s=%s" % (k, v) for k, v in params.items()])
    return endpoint


def rest_upload_file(dest, endpoint, path, session_key):
    conn = httplib.HTTPSConnection(dest)
    conn.connect()
    conn.putrequest('POST', endpoint)
    conn.putheader('Authorization', 'Splunk ' + session_key)
    conn.putheader('X-File-Name', os.path.basename(path))
    conn.putheader('Content-Type', 'tar')
    conn.putheader('X-Splunk-Input-Mode', 'streaming')

    filesize = os.path.getsize(path)
    logger.debug("Size of path=%s is filesize=%d" % (path, filesize))

    conn.endheaders()

    log_fd = open(path, 'rb')
    logger.debug('Opened path=%s' % path)
    while True:
        log_content = log_fd.read(1000)
        if not log_content:
            break
        conn.send(log_content)
    logger.debug('Closing connection.')
    conn.close()
    logger.info("Uploaded %s" % path)


def main():
    session_key = get_session_key(
        mgmt_host_port=mgmt_host_port, username=username, password=password)
    for arg in sys.argv[1:]:
        params['source'] = os.path.basename(arg)
        rest_upload_file(
            dest=mgmt_host_port, endpoint=rest_build_endpoint(params), path=arg,
            session_key=session_key)
        logger.info('Waiting 5 seconds for Splunk to index the file.')
        time.sleep(5)
        search_query = urllib.quote(
            "search source=\"%s\"" % os.path.basename(arg))
        search_url = (
            "http://%s:8000/en-US/app/search/flashtimeline?q=%s"
            % (splunk_server, search_query))
        show_results(search_url=search_url)


if __name__ == '__main__':
    main()
