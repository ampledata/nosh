#!/usr/bin/env python
"""nosh.py - Eat a little data, using Splunk.

Features
========
    nosh.py uploads a local file to a remote Splunk server and opens a web browser to the Splunk web interface, 
    allowing you to search the contents of your file, report on contents within the file, and more.
    
Installation
============
    1. Open nosh.py in your favorite $EDITOR and set splunkServer, username and password.
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
    nosh.py can be configured as a Mac OS X Service. When enabled, you can use Mac OS X contextual menus 
    to select and index files using Splunk.
    
    To create a custom Mac OS X Service for nosh.py:
        1. Open Automator.app
        2. When prompted for a template, select 'Service' (or go to File -> New).
        3. Set 'Service receives selected' to 'files or folders' in 'any application'.
        4. In your Actions Library select 'Run Shell Script'.
        5. In the 'Run Shell Script' action set 'Pass input:' to 'as arguments'.
        6. For the acutal shell script to run, enter: /path/to/nosh.py $*
        7. File -> Save and set 'Save Service as:' to 'Index with Splunk'.
                
Meta
====
    Author: Greg Albrecht (gba@gregalbrecht.com)
    Version: $Id: //splunk/qa/nosh/nosh.py#6 $
"""
## Change Me!   <----- CHANGE STUFF HERE <------ HEY LOOK AT ME
splunkServer    = 'localhost'
username        = 'admin'
password        = 'changeme'

import os
import sys
import socket
import urllib
import httplib
import logging

from xml.dom import minidom
from time import sleep
from logging.handlers import *

## Probably nothing to change here.
# defaultHost sets the 'host' field to associate with uploaded data. Defaults to your hostname.
defaultHost             = socket.gethostname()
splunkServerMgmtPort    =   "8089"
splunkServerHTTPPort    =   "8000"

## Definitely nothing to change here.
__author__      = "$Author: gba $"
__version__     = "$Id: //splunk/qa/nosh/nosh.py#6 $"
mgmtHostPort    =   ':'.join((splunkServer,splunkServerMgmtPort))
params          =   { "host" : defaultHost }
logger          =   logging.getLogger("nosh")
cliLogger       =   logging.StreamHandler()
cliLoggerFormat =   logging.Formatter("%(levelname)s - %(message)s")
logger.setLevel(logging.INFO)
cliLogger.setLevel(logging.INFO)
cliLogger.setFormatter(cliLoggerFormat)
logger.addHandler(cliLogger)

def showResults ( searchURL ) :
    try:
        import webbrowser
        logger.info( "About to open a this URL in a browser: %s" % searchURL )
        webbrowser.open(searchURL)
    except:
        logger.info( "Have at it: %s" % searchURL )


def getSessionKey ( mgmtHostPort, username, password ):
    HTTPConn = httplib.HTTPSConnection(mgmtHostPort)
    HTTPConn.request(   method="POST", url='/services/auth/login', headers={}, 
                        body=urllib.urlencode( { 'username':username, 'password':password } ) )
    serverResponse = HTTPConn.getresponse()
    if not serverResponse.status == 200:
        logger.error( "Server did not return 200 (it returned '%s %s'). Perhaps you didn't set your password?" % \
            (serverResponse.status, serverResponse.reason) )
        raise Exception, ( serverResponse.status, serverResponse.reason )
    responseConent = serverResponse.read()
    return minidom.parseString(responseConent).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue


def restBuildEndpoint ( params ):
    endpoint = "/services/receivers/stream"
    if params:
        endpoint += "?" + "&".join(["%s=%s" % (k,v) for k,v in params.items()])
    return endpoint


def restUploadFile ( dest, endpoint, path, sessionKey ):
    conn = httplib.HTTPSConnection(dest)
    conn.connect()
    conn.putrequest('POST', endpoint)
    conn.putheader('Authorization', 'Splunk ' + sessionKey)
    conn.putheader('X-File-Name', os.path.basename(path))
    conn.putheader('Content-Type', 'tar')
    conn.putheader('X-Splunk-Input-Mode', 'streaming')
    
    filesize = os.path.getsize(path)
    logger.debug( "Size of path=%s is filesize=%d" % (path, filesize) )
    
    conn.endheaders()
    
    f = open(path, 'rb')
    logger.debug( 'Opened path=%s' % path )
    while True:
        s = f.read(1000)
        if not s:
            break
        conn.send(s)    
    logger.debug( 'Closing connection.' )
    conn.close()
    logger.info( "Uploaded %s" % path )


def main ():
    sessionKey = getSessionKey( mgmtHostPort=mgmtHostPort, username=username, password=password )
    for f in sys.argv[1:]:
        params["source"] = os.path.basename(f)
        restUploadFile( dest=mgmtHostPort, endpoint=restBuildEndpoint(params), path=f, sessionKey=sessionKey )
        logger.info( "Waiting 5 seconds for Splunk to index the file." )
        sleep(5)
        searchQuery = urllib.quote("search source=\"%s\"" % os.path.basename(f))
        searchURL   = "http://%s:8000/en-US/app/search/flashtimeline?q=%s" % (splunkServer,searchQuery)
        showResults(searchURL=searchURL)


if __name__ == '__main__':
    main()