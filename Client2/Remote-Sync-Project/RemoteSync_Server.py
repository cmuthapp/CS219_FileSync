import socket
import threading
import hashlib
import re
import getpass
import os
import dill
import librsync

from RemoteSync_Client import Client
from RemoteSync_Client import RemoteSync

class ThreadedServer(object):
    def __init__(self):
        self.IPADDRESS = "192.168.1.14"
        self.PORT = 2122
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.IPADDRESS, self.PORT))

    def listen(self):
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(60)
            threading.Thread(target = self.listenToClient,args = (client,address)).start()

    def listenToClient(self, client, address):
        size = 1024
        while True:
            try:
                data = client.recv(size)
                if data:
                    # Print data
                    print "Received Data: ",data
                    self.ProcessMetaData(data)
                else:
                    raise error('Client Disconnected')
            except:
                client.close()
                return False

    def ProcessMetaData(self, metaData):
        metaList = metaData.split(":")
        if len(metaList) == 6:
            command = metaList[0]
            metaFilePath = metaList[1]
            metaDestIP = metaList[2]
            metaUserName = metaList[3]
            metaPassword = metaList[4]
            metaHash = metaList[5]

        if command == "PUSH":
            receivedData = command + ":" + metaFilePath + ":" + metaDestIP + ":" + metaUserName + ":" + metaPassword
            print "test connectted"

            if str(metaHash) == self.CalculatedHash(receivedData):
                print "Hash Matched"
                objRemoteSync = RemoteSync(metaDestIP, 22, metaUserName, metaPassword)
                #print "1"
                generatedFileName = self.GenerateLocalFileName(metaFilePath)
                #print "2"
                localDeltaPath = "/home/"+getpass.getuser()+"/RemoteSync/"+str(self.ParseDeltaFileName(metaFilePath))
                #print "3"

                if os.path.exists(localDeltaPath):
                    self.Cleanup(localDeltaPath)

                objRemoteSync.GetFile(localDeltaPath, metaFilePath)
                #print "4"
                self.PatchLocalFile(localDeltaPath)
                #print "9"
                self.Cleanup(localDeltaPath)
                del objRemoteSync

                #ACK Part
                objACKClient = Client()
                metaACKString = "SYNC ACK:" + self.IPADDRESS
                objACKClient.SendData(metaACKString)

            else:
                #Send Negative ACK so that client can resend
                print "Data Changed"

    def Cleanup(self, metaFilePath):
        os.remove(metaFilePath)

    def PatchLocalFile(self, deltaPath):
        finalLocalName = self.GenerateLocalFileName(deltaPath)
        finalLocalFilePath = "/home/"+getpass.getuser()+"/RemoteSync/"+finalLocalName
        finalLocalHiddenFilePath = "/home/"+getpass.getuser()+"/RemoteSync/."+finalLocalName
        print finalLocalName
        print finalLocalFilePath
        print finalLocalHiddenFilePath
        print deltaPath

        #synced = file("/home/"+getpass.getuser()+"/RemoteSync/"+".Synced_"+finalLocalName, 'wb')

        if os.path.exists(finalLocalFilePath):
            print "Deleted Already Present File"
            self.Cleanup(finalLocalFilePath)

        if not os.path.exists(finalLocalHiddenFilePath):
            print "Create a Hidden File"
            self.CreateEmptyFile(finalLocalHiddenFilePath)

        #Open delta from synced file
        restoredDelta = dill.load(open(deltaPath))

        #Clear a file first
        synced = file(finalLocalFilePath, 'wb')

        dst = file(finalLocalHiddenFilePath, 'rb')

        librsync.patch(dst, restoredDelta, synced)

        if os.path.exists(finalLocalHiddenFilePath):
            self.Cleanup(finalLocalHiddenFilePath)
            #self.CreateEmptyFile(finalLocalHiddenFilePath)
            print "Cleared the Hidden File"

        self.Cleanup(deltaPath)
        #self.CopyContent(finalLocalFilePath,finalLocalHiddenFilePath)

        src.close()
        dst.close()
        print "8"

    def CreateEmptyFile(self, filePath):
        open(filePath, "w").close

    def ParseDeltaFileName(self, filePath):
        return filePath.split("/")[-1]

    def GenerateLocalFileName(self, filePath):
        deltaFileName = filePath.split("/")[-1]
        pattern = re.compile("\.Delta\_(.*)")
        newFileName = pattern.findall(deltaFileName)[0]
        return newFileName

    def CalculatedHash(self, receivedData):
        hashObject = hashlib.sha1(receivedData)
        hexDigest = hashObject.hexdigest()
        return str(hexDigest)

    def CopyContent(self, sourceFilePath, destinationFilePath):
        #print "Source File: ",sourceFileName
        #print "Destination File: ",destinationFileName
        with open(destinationFilePath, 'w+') as output, open(sourceFilePath, 'r') as input:
            while True:
                data = input.read(100000)
                if data == '':
                    break
                output.write(data)

if __name__ == "__main__":
    objServer = ThreadedServer()
    objServer.listen()

    #sudo fuser -k 2122/tcp
