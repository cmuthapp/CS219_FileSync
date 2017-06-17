import socket
import sys
import select
import os
import librsync    #sudo apt-get install librsync-dev
import dill        #pip install dill
import paramiko #sudo apt-get install python-paramiko
import hashlib
import getpass
import ssl #sudo apt-get install libssl-dev

import os.path
from subprocess import call
import pyinotify    #sudo apt-get install python-pyinotify


from Helpers.Crawler import Crawler
from Helpers.RemoteSync import RemoteSync

class Client(object):
    def __init__(self):
        self.IPADDRESS = "192.168.1.15"
        self.USER_IPADDRESS = "192.168.1.32"
        self.PORT = 2122
        self.LOCK = ""
        self.CERTIFICATE_PATH = '/home/'+ getpass.getuser() +'/Client/SSL_CERT'

    #Function for sending data on one side
    def SendData(self, string):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #We are using SSLv23 Tunnel for encrypting the communication between clients and Master
        ssl_sock = ssl.wrap_socket(sock,
                                   ca_certs=self.CERTIFICATE_PATH,
                                   cert_reqs=ssl.CERT_REQUIRED)
        ssl_sock.connect((self.IPADDRESS, self.PORT))

        print "SENDING DATA => [%s]" % (string)

        #Sending String
        ssl_sock.send(string)
        ssl_sock.close()
        sock.close()

    #Function for sending and receiving data
    def SendAndReceiveData(self, string):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = ssl.wrap_socket(sock,
                                   ca_certs=self.CERTIFICATE_PATH,
                                   cert_reqs=ssl.CERT_REQUIRED)
        ssl_sock.connect((self.IPADDRESS, self.PORT))
        print "SENDING DATA => [%s]" % (string)
        ssl_sock.send(string)

        #Waiting to receive connection back from server
        recv_string = ""
        try:
            #Receiving String
            recv_string = ssl_sock.recv(1024)
            print "RECEIVED DATA => [%s]" % (recv_string)
            ssl_sock.close() #Closing the SSL tunnel
            sock.close()

        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
            sys.exit(0)

        return recv_string

    #Function for creating PUSH meta string
    def CreateMetaString(self, fileName, tempDirectory, version):
        metaString = "PUSH:"
        metaString = metaString + self.USER_IPADDRESS + ":" + tempDirectory + "/" + ".Delta_"+fileName + ":" + version

        hashObject = hashlib.sha1(metaString)
        hexDigest = hashObject.hexdigest()

        metaString = metaString + ":" + str(hexDigest)

        return metaString

    #Function for creating GET LOCK meta string
    def CreateGetLockMetaString(self, fileName):
        metaString = "GET LOCK:"
        metaString = metaString + fileName

        hashObject = hashlib.sha1(metaString)
        hexDigest = hashObject.hexdigest()

        metaString = metaString + ":" + str(hexDigest)

        return metaString

    #Function for creating RELEASE LOCK meta string
    def CreateReleaseLockMetaString(self, fileName):
        metaString = "RELEASE LOCK:"
        metaString = metaString + fileName

        hashObject = hashlib.sha1(metaString)
        hexDigest = hashObject.hexdigest()

        metaString = metaString + ":" + str(hexDigest)

        return metaString

    #Function for creating DELETE meta string
    def CreateDeleteMetaString(self, fileName):
        metaString = "DELETE:"
        metaString = metaString + fileName

        hashObject = hashlib.sha1(metaString)
        hexDigest = hashObject.hexdigest()

        metaString = metaString + ":" + str(hexDigest)

        return metaString

    #Function for deleting a file
    def Cleanup(self, directory, metaFilePath):
        os.remove(directory+ "/" +metaFilePath)

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self):
        self.objSocketClient = Client()
        self.objCrawler = Crawler()
        self.objRemoteSync = RemoteSync()
        self.test = False
        self.tempPath = "/tmp/RemoteSync"
        self.objCrawler.LoadVersionHistory() #Loading the local version history

    #Get File name from the file path
    def ParseDeltaFileName(self, filePath):
        return filePath.split('/')[-1]

    #This listener function is called when a file inside of "RemoteSync" directory is opened
    def process_IN_OPEN(self, event):
        print "IN_OPEN: ",event.pathname #event.pathname contains the path of the file opened inside the RemoteSync directory

        modifiedFile = self.ParseDeltaFileName(event.pathname) #Get the file name from the file path

        if not modifiedFile[0] == "." and os.path.isfile(event.pathname): #To check if the filepath is not directory and is not a temp hidden file
            if not self.objCrawler.CheckIfExists(self.tempPath,"."+modifiedFile): #Check if the hidden temp file exists in /tmp/RemoteSync
                #print "Open Called!"
                self.objCrawler.CreateHiddenFile(self.tempPath, modifiedFile) #If not then create a hidden file for tracking previous version of files in RemoteSync
            del modifiedFile

    #This listener function is called when a file is saved with new content
    def process_IN_CLOSE_WRITE(self, event):
        print "CLOSE_WRITE: ",event.pathname
        modifiedFile = self.ParseDeltaFileName(event.pathname)

        if os.path.isfile(event.pathname) and not modifiedFile[0] == ".":
            print "REQUESTING LOCK ... "

            #Send lock get request to master
            lockReply = self.objSocketClient.SendAndReceiveData(self.objSocketClient.CreateGetLockMetaString(modifiedFile))
            lockReplyList = lockReply.split(":")
            self.objSocketClient.LOCK = lockReplyList[0]
            LockedFile = lockReplyList[1] #Parsing Lock reply from master
            versionNumber = lockReplyList[2]
            lockHash = lockReplyList[3]

            hashObject = hashlib.sha1(self.objSocketClient.LOCK + ":" + LockedFile + ":" + versionNumber)
            hexDigest = hashObject.hexdigest()

            #Hash Check
            if str(hexDigest) == lockHash:
                print "HASH UNCHANGED"
                if self.objSocketClient.LOCK == "GRANT":
                    print "LOCK GRANTED"
                    if not modifiedFile[0] == "." and os.path.isfile(event.pathname):

                        #The version number if obtained from master, so as to maintain consistency. Update it once received in the LOCK reply.
                        self.objCrawler.UpdateVersionHistory(LockedFile, versionNumber)
                        self.objCrawler.WriteVersionLog() #Write the version number to the version log file

                        #Calculate and save delta
                        self.objCrawler.CalculateDelta(self.tempPath, modifiedFile) #Calculate delta between the new changes and the previously saved hidden file.

                        #Create the string to send to Master
                        metaString = self.objSocketClient.CreateMetaString(modifiedFile, self.tempPath, self.objCrawler.GetFileVersion(modifiedFile))

                        #Send data to master
                        print "PUSH META STRING SENT"
                        self.objSocketClient.SendData(metaString)

                        #Update hidden temp file
                        self.objCrawler.CopyFile(self.tempPath, modifiedFile)

                        #LOCK Release
                        #Time to release Lock
                        lockReply = self.objSocketClient.SendAndReceiveData(self.objSocketClient.CreateReleaseLockMetaString(modifiedFile))
                        lockReplyList = lockReply.split(":")
                        self.objSocketClient.LOCK = lockReplyList[0]
                        unLockedFile = lockReplyList[1]
                        unlockHash = lockReplyList[2]

                        hashObject = hashlib.sha1(self.objSocketClient.LOCK + ":" + unLockedFile)
                        hexDigest = hashObject.hexdigest()

                        #Check Hash
                        if str(hexDigest) == unlockHash:
                            print "HASH UNCHANGED"
                            if self.objSocketClient.LOCK == "GRANT":
                                print "LOCK RELEASED"
                            else:
                                print "LOCK NOT RELEASED"
                        else:
                            print "HASH CHANGED"
                #Lock is currently being used by another user
                elif self.objSocketClient.LOCK == "NO GRANT":
                    print "CANNOT ACQUIRE LOCK"
            else:
                print "HASH CHANGED"

            self.objSocketClient.LOCK = ""
            del modifiedFile

    #This listener is called when a file is deleted from the RemoteSync directory
    def process_IN_DELETE(self, event):
        deletedFile = self.ParseDeltaFileName(event.pathname)

        if not deletedFile[0] == ".":
            print "DELETE: ",deletedFile
            print "SEND DELETE META STRING"

            #Remove entry from the version dictionary
            self.objCrawler.RemoveVersionLog(deletedFile)
            self.objCrawler.WriteVersionLog() #Update the version log

            #Send Delete meta string to the master
            deleteReply = self.objSocketClient.SendAndReceiveData(self.objSocketClient.CreateDeleteMetaString(deletedFile))
            status = deleteReply.split(":")[0]
            statusHash = deleteReply.split(":")[1]

            hashObject = hashlib.sha1(status)
            hexDigest = hashObject.hexdigest()

            #Hash Check
            if str(hexDigest) == statusHash:
                print "HASH UNCHANGED"
                if deleteReply.split(':')[0] == "ACK":
                    print "FILES DELETED FROM ALL MACHINES"
                else:
                    print "CANNOT DELETE FROM OTHER MACHINES"
            else:
                print "HASH CHANGED"

if __name__ == "__main__":
    #Check if target directory exists?
    if not os.path.isdir("/tmp/RemoteSync"):
        #Create if it doesn't
        os.makedirs("/tmp/RemoteSync")

    wm = pyinotify.WatchManager() 	## Watch Manager
    mask = pyinotify.IN_OPEN | pyinotify.IN_CLOSE_WRITE |  pyinotify.IN_DELETE  ## watched events
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    notifier.coalesce_events()
    wdd = wm.add_watch('/home/'+ getpass.getuser() +'/RemoteSync/', mask, rec=True)   ##directory to watch. this can be passed in as parameter if required.

    notifier.loop()
