#!/usr/bin/python

import socket
import sys
import os
import librsync    #sudo apt-get install librsync-dev
import dill        #pip install dill
import paramiko #sudo apt-get install python-paramiko
import hashlib
import getpass

from Helpers.Crawler import Crawler

class RemoteSync(object):

    def __init__(self, hostname, port, client, password):
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

    def PutFile(self, localFilePath, remoteFilePath):
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
            sessionHandle.put(localFilePath, remoteFilePath)
            sessionHandle.close()
            handle.close()

        except Exception, e:
            print '*** Put Caught exception: %s: %s' % (e.__class__, e)
            try:
                handle.close()
            except:
                pass

    def Usage(self, cmd=None):
        usageFull = """\

        RemoteSync -- A python wrapper for remote sync.

        Usage:
            RemoteSync.py <File-Name> <command>

        Main Commands:
            push        : push local changes to remote
        """
        print usageFull


class Client(object):
    def __init__(self):
        self.IPADDRESS = "192.168.1.15"
        self.USER_IPADDRESS = "192.168.1.13"
        self.PORT = 2122

    def SendData(self, string):
        # SOCK_STREAM == a TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #sock.setblocking(0)  # optional non-blocking
        sock.connect((self.IPADDRESS, self.PORT))

        print "sending data => [%s]" % (string)

        sock.send(string)
        sock.close()

    def CreateMetaString(self, fileName, localDirectory):
        metaString = ""
        metaString = metaString + self.USER_IPADDRESS + ":" + localDirectory + ".Delta_"+fileName

        hashObject = hashlib.sha1(metaString)
        hexDigest = hashObject.hexdigest()

        metaString = metaString + ":" + str(hexDigest)

        return metaString


if __name__ == "__main__":
    objSocketClient = Client()
    objCrawler = Crawler()
    objRemoteSync = RemoteSync()

    try:
        modifiedFile = sys.argv[1]
        argsIN = sys.argv[2]
    except:
        objRemoteSync.Usage()
        sys.exit(2)

    if argsIN in ['help','-h','--help', '-help']:
        objRemoteSync.Usage()
        sys.exit(2)
    elif argsIN in ['push', '-push']:
        if not objCrawler.CheckIfExists(modifiedFile):
            #The pushed file doesn't exists
            print "Error: File doesn't exist ..."

        #Check for hidden file: if exists, then not the first version
        if not objCrawler.CheckIfExists("."+modifiedFile):
            objCrawler.CreateHiddenFile(modifiedFile)

        #Calculate and save delta
        objCrawler.CalculateDelta(modifiedFile)

        #Create the string to send to Master
        metaString = objSocketClient.CreateMetaString(modifiedFile, objRemoteSync.localDirectory)

        #Send data to master
        objSocketClient.SendData(metaString)

        #Save Previous Version
        objCrawler.CopyContent(modifiedFile, "."+modifiedFile)
