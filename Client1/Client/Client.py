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


from Helpers.Crawler import Crawler
from Helpers.RemoteSync import RemoteSync

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
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.IPADDRESS, self.PORT))
        print "sending data => [%s]" % (string)
        sock.send(string)

        #Waiting to receive connection back from server
        recv_string = ""
        try:
            recv_string = sock.recv(1024)
            print "received data => [%s]" % (recv_string)
            sock.close()

        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
            print "Error Man"
            sys.exit(0)

        print "Received LOCK"
        return recv_string

    def CreateMetaString(self, fileName, tempDirectory):
        metaString = "PUSH:"
        metaString = metaString + self.USER_IPADDRESS + ":" + tempDirectory + "/" + ".Delta_"+fileName

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

    def CreateDeleteMetaString(self, fileName):
        metaString = "DELETE:"
        metaString = metaString + fileName

        hashObject = hashlib.sha1(metaString)
        hexDigest = hashObject.hexdigest()

        metaString = metaString + ":" + str(hexDigest)

        return metaString

    def Cleanup(self, directory, metaFilePath):
        os.remove(directory+ "/" +metaFilePath)

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self):
        self.objSocketClient = Client()
        self.objCrawler = Crawler()
        self.objRemoteSync = RemoteSync()
        self.test = False
        self.tempPath = "/tmp/RemoteSync"


    def ParseDeltaFileName(self, filePath):
        return filePath.split('/')[-1]

   # i = 0
    def process_IN_OPEN(self, event):
        print "IN_OPEN",event.pathname

        modifiedFile = self.ParseDeltaFileName(event.pathname)

        if not modifiedFile[0] == "." and os.path.isfile(event.pathname):
            if not self.objCrawler.CheckIfExists(self.tempPath,"."+modifiedFile):
                print "Open Called!"
                self.objCrawler.CreateHiddenFile(self.tempPath, modifiedFile)
            del modifiedFile

    def process_IN_CLOSE_WRITE(self, event):
        print "CLOSE_WRITE",event.pathname
        modifiedFile = self.ParseDeltaFileName(event.pathname)

        if os.path.isfile(event.pathname) and not modifiedFile[0] == ".":
            print "TRUE: ",event.pathname

        #if self.testCounter == 0:
        if os.path.isfile(event.pathname) and not modifiedFile[0] == ".":
            print "Send Data"

            #if os.path.isfile(self.tempPath + "/.Delta_" +modifiedFile):
                #print "----->IMPORTANT: Delta Deleted"
                #self.objSocketClient.Cleanup(self.tempPath, ".Delta_" +modifiedFile)

            #In open file list
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
                    print "Close: ",modifiedFile
                    if not modifiedFile[0] == "." and os.path.isfile(event.pathname):
                        #Calculate and save delta
                        self.objCrawler.CalculateDelta(self.tempPath, modifiedFile)

                        #Create the string to send to Master
                        metaString = self.objSocketClient.CreateMetaString(modifiedFile, self.tempPath)

                        #Send data to master
                        self.objSocketClient.SendData(metaString)

                        #Update hidden temp file
                        self.objCrawler.CopyFile(self.tempPath, modifiedFile)

                        #Delete Previous Version
                        #self.objSocketClient.Cleanup(self.tempPath, "."+modifiedFile)

                        #LOCK Release
                        #Time to release Lock
                        lockReply = self.objSocketClient.SendAndReceiveData(self.objSocketClient.CreateReleaseLockMetaString(modifiedFile))
                        #lockReply = self.objSocketClient.ReceiveData()
                        lockReplyList = lockReply.split(":")
                        self.objSocketClient.LOCK = lockReplyList[0]
                        unLockedFile = lockReplyList[1]
                        unlockHash = lockReplyList[2]

                        hashObject = hashlib.sha1(self.objSocketClient.LOCK + ":" + unLockedFile)
                        hexDigest = hashObject.hexdigest()

                        if str(hexDigest) == unlockHash:
                            print "Hash Unchanged"
                            if self.objSocketClient.LOCK == "GRANT":
                                print "Lock Released"
                            else:
                                print "Lock not released"
                        else:
                            print "Hash CHanged"

                elif self.objSocketClient.LOCK == "NO GRANT":
                    print "Cannot Acquire Lock"
                    self.testCounter = 0
            else:
                print "Hash Changed"

            self.objSocketClient.LOCK = ""
            #Delete Previous Version

            del modifiedFile

    def process_IN_DELETE(self, event):
        deletedFile = self.ParseDeltaFileName(event.pathname)
        print "Delete Reached"
        if not deletedFile[0] == ".":
            print "DELETE: ",deletedFile
            deleteReply = self.objSocketClient.SendAndReceiveData(self.objSocketClient.CreateDeleteMetaString(deletedFile))
            status = deleteReply.split(":")[0]
            statusHash = deleteReply.split(":")[1]

            hashObject = hashlib.sha1(status)
            hexDigest = hashObject.hexdigest()

            if str(hexDigest) == statusHash:
                print "Hash Unchanged"
                if deleteReply.split(':')[0] == "ACK":
                    print "Files Deleted From all Machines"
                else:
                    print "Cannot Delete From Other Machines"
            else:
                print "Hash Changed"

if __name__ == "__main__":
    if not os.path.isdir("/tmp/RemoteSync"):
        os.makedirs("/tmp/RemoteSync")

    wm = pyinotify.WatchManager() 	## Watch Manager
    mask = pyinotify.IN_OPEN | pyinotify.IN_CLOSE_WRITE |  pyinotify.IN_DELETE #| pyinotify.IN_MODIFY #| pyinotify.IN_CLOSE_NOWRITE   ## watched events
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    notifier.coalesce_events()
    wdd = wm.add_watch('/home/'+ getpass.getuser() +'/RemoteSync/', mask, rec=True)   ##directory to watch. this can be passed in as parameter if required.

    notifier.loop()
