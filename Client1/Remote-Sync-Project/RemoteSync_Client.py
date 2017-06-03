#!/usr/bin/python

import socket
import sys
import os
import librsync    #sudo apt-get install librsync-dev
import dill        #pip install dill
import paramiko #sudo apt-get install python-paramiko
import hashlib
import getpass

import os.path
from subprocess import call
import pyinotify    #sudo apt-get install python-pyinotify


from Helpers.Crawler import Crawler

class RemoteSync(object):

    def __init__(self):
        self.hostname = '192.168.1.15' # remote hostname where SSH server is running
        self.port = 22

        self.localDirectory = "/home/"+getpass.getuser()+"/RemoteSync/"

    def GetFile(self, localDirectoy, remoteDirectory, localFileName, remoteFileName):
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
            sessionHandle.get(remoteDirectory+remoteFileName, localDirectoy+localFileName)
            sessionHandle.close()
            handle.close()

        except Exception, e:
            print '*** Get Caught exception: %s: %s' % (e.__class__, e)
            try:
                handle.close()
            except:
                pass

    def PutFile(self, localDirectoy, remoteDirectory, localFileName, remoteFileName):
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
            sessionHandle.put(localDirectoy+localFileName, remoteDirectory+remoteFileName)
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
        self.LOCK = ""

    def SendData(self, string):
        # SOCK_STREAM == a TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #sock.setblocking(0)  # optional non-blocking
        sock.connect((self.IPADDRESS, self.PORT))

        print "sending data => [%s]" % (string)

        sock.send(string)
        sock.close()

    def SendAndReceiveData(self, string):
        # SOCK_STREAM == a TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #sock.setblocking(0)  # optional non-blocking
        sock.connect((self.IPADDRESS, self.PORT))

        print "sending data => [%s]" % (string)

        sock.send(string)
        recv_string = sock.recv(1024)
        print "received data => [%s]" % (recv_string)
        sock.close()

        return recv_string

    def CreateMetaString(self, fileName, localDirectory):
        metaString = "PUSH:"
        metaString = metaString + self.USER_IPADDRESS + ":" + localDirectory + ".Delta_"+fileName

        hashObject = hashlib.sha1(metaString)
        hexDigest = hashObject.hexdigest()

        metaString = metaString + ":" + str(hexDigest)

        return metaString

    def CreateGetLockMetaString(self, fileName):
        metaString = "GET LOCK:"
        metaString = metaString + fileName

        hashObject = hashlib.sha1(metaString)
        hexDigest = hashObject.hexdigest()

        metaString = metaString + ":" + str(hexDigest)

        return metaString

    def CreateReleaseLockMetaString(self, fileName):
        metaString = "RELEASE LOCK:"
        metaString = metaString + fileName

        hashObject = hashlib.sha1(metaString)
        hexDigest = hashObject.hexdigest()

        metaString = metaString + ":" + str(hexDigest)

        return metaString

    def Cleanup(self, metaFilePath):
        os.remove(metaFilePath)

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self):
        self.objSocketClient = Client()
        self.objCrawler = Crawler()
        self.objRemoteSync = RemoteSync()


    def ParseDeltaFileName(self, filePath):
        return filePath.split('/')[-1]

   # i = 0
    def process_IN_OPEN(self, event):
        modifiedFile = self.ParseDeltaFileName(event.pathname)

        #Send lock get request to master
        lockReply = self.objSocketClient.SendAndReceiveData(self.objSocketClient.CreateGetLockMetaString(modifiedFile))
        #lockReply = self.objSocketClient.ReceiveData()
        lockReplyList = lockReply.split(":")
        self.objSocketClient.LOCK = lockReplyList[0]
        LockedFile = lockReplyList[1]
        lockHash = lockReplyList[2]

        hashObject = hashlib.sha1(self.objSocketClient.LOCK + ":" + LockedFile)
        hexDigest = hashObject.hexdigest()

        if str(hexDigest) == lockHash:
            print "Hash Unchanged"
            if self.objSocketClient.LOCK == "GRANT":
                print modifiedFile
                print "Read This Bro: ",event.pathname
            	if (not modifiedFile[0] == "." and os.path.isfile(event.pathname) and not "Delta" in self.ParseDeltaFileName(event.pathname) and not os.path.isfile(self.objCrawler.directoryPath+"."+modifiedFile)):
                    if not self.objCrawler.CheckIfExists("."+modifiedFile):
                        self.objCrawler.CreateHiddenFile(modifiedFile)
                    del modifiedFile
            elif self.objSocketClient.LOCK == "NO GRANT":
                print "Cannot Acquire Lock"
        else:
            print "Hash Changed"

#    def process_IN_CLOSE_NOWRITE(self, event):
#        print "file closed without changes: ", event.pathname
    def process_IN_CLOSE_WRITE(self, event):
        modifiedFile = self.ParseDeltaFileName(event.pathname)
        print "Close: ",modifiedFile

    	if (not modifiedFile[0] == "." and os.path.isfile(event.pathname) and not "Delta" in self.ParseDeltaFileName(event.pathname)):
        	#Calculate and save delta
            self.objCrawler.CalculateDelta(modifiedFile)

            #Create the string to send to Master
            metaString = self.objSocketClient.CreateMetaString(modifiedFile, self.objRemoteSync.localDirectory)

            #Send data to master
            self.objSocketClient.SendData(metaString)

            #Delete Previous Version
            self.objSocketClient.Cleanup("/home/"+getpass.getuser()+"/RemoteSync/"+"."+modifiedFile)
            del modifiedFile

    def process_IN_CLOSE_NOWRITE(self, event):
        modifiedFile = self.ParseDeltaFileName(event.pathname)

        #Send lock get request to master
        self.objSocketClient.SendData(self.objSocketClient.CreateReleaseLockMetaString(modifiedFile))
        lockReply = self.objSocketClient.recv()
        lockReplyList = lockReply.split(":")
        self.objSocketClient.LOCK = lockReplyList[0]
        LockedFile = lockReplyList[1]
        lockHash = lockReplyList[2]

        hashObject = hashlib.sha1(self.objSocketClient.LOCK + ":" + LockedFile)
        hexDigest = hashObject.hexdigest()

        if str(hexDigest) == lockHash:
            print "Hash Unchanged"
            if self.objSocketClient.LOCK == "GRANT":
                print "Lock Released"
            elif self.objSocketClient.LOCK == "NO GRANT":
                print "Cannot Release Lock At This Moment"
        else:
            print "Hash Changed"


if __name__ == "__main__":
    wm = pyinotify.WatchManager() 	## Watch Manager
    mask = pyinotify.IN_OPEN | pyinotify.IN_CLOSE_WRITE | pyinotify.IN_CLOSE_NOWRITE  #| pyinotify.IN_MODIFY #| pyinotify.IN_CLOSE_NOWRITE   ## watched events
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    notifier.coalesce_events()
    wdd = wm.add_watch('/home/client1/RemoteSync/', mask, rec=True)   ##directory to watch. this can be passed in as parameter if required.

    notifier.loop()
