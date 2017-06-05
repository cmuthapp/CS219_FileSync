#!/usr/bin/python

import socket
import sys
import select
import os
import librsync    #sudo apt-get install librsync-dev
import dill        #pip install dill
import paramiko #sudo apt-get install python-paramiko
import hashlib
import getpass

import os.path
from subprocess import call
import pyinotify    #sudo apt-get install python-pyinotify

class RemoteSync(object):

    def __init__(self, hostname=None, port=None, client=None, password=None):
        self.hostname = hostname
        self.port = port
        self.username = client
        self.password = password

        self.localDirectory = "/home/"+getpass.getuser()+"/RemoteSync/"

    def GetFile(self, localFilePath, remoteFilePath):
        try:
            print 'Establishing SSH connection to:', self.hostname, self.port, '...'
            handle = paramiko.Transport((self.hostname, self.port))
            handle.start_client()

            handle.auth_password(username=self.username, password=self.password)

            if handle.is_authenticated():
                print 'Connection Established ...'
            else:
                print 'Connection Failed ...'

            sessionHandle = paramiko.SFTPClient.from_transport(handle)
            sessionHandle.get(remoteFilePath, localFilePath)
            sessionHandle.close()
            handle.close()

        except Exception, e:
            print '*** Get Caught exception: %s: %s' % (e.__class__, e)
            try:
                handle.close()
            except:
                pass
