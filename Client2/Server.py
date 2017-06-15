import socket
import threading
import hashlib
import re
import getpass
import os
import dill
import librsync
from shutil import copyfile
import ssl

from Client import Client
from Client import RemoteSync

class ThreadedServer(object):
    def __init__(self):
        self.IPADDRESS = "192.168.1.32"
        self.PORT = 2122
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.IPADDRESS, self.PORT))
        self.tempPath = "/tmp/RemoteSync"
        self.CERTIFICATE_PATH = '/home/'+ getpass.getuser() +'/Client/SSL_CERT'
        self.KEY_PATH = '/home/'+ getpass.getuser() +'/Client/SSL_KEY'

    def listen(self):
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(60)
            threading.Thread(target = self.listenToClient,args = (client,address)).start()

    def listenToClient(self, client, address):
        size = 1024
        self.connstream = ssl.wrap_socket(client,
                                          server_side=True,
                                          certfile=self.CERTIFICATE_PATH,
                                          keyfile=self.KEY_PATH,
                                          ssl_version=ssl.PROTOCOL_SSLv23
                                          )

        while True:
            try:
                data = self.connstream.recv(size)
                if data:
                    # Print data
                    print "RECEIVED DATA: ",data
                    self.ProcessMetaData(data)
                    client.close()
                    self.connstream.close()
                else:
                    raise error('Client Disconnected')
            except:
                client.close()
                self.connstream.close()
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
        if len(metaList) == 3:
            command = metaList[0]
            metafileName = metaList[1]
            metaHash = metaList[2]

        if command == "PUSH":
            receivedData = command + ":" + metaFilePath + ":" + metaDestIP + ":" + metaUserName + ":" + metaPassword

            if str(metaHash) == self.CalculatedHash(receivedData):
                print "HASH UNCHANGED"
                objRemoteSync = RemoteSync(metaDestIP, 22, metaUserName, metaPassword)
                #print "1"
                generatedFileName = self.GenerateLocalFileName(metaFilePath)
                #print "2"
                localDeltaPath = self.tempPath+"/"+str(self.ParseDeltaFileName(metaFilePath))
                #print "3"

                #if os.path.exists(localDeltaPath):
                    #self.Cleanup(localDeltaPath)

                objRemoteSync.GetFile(localDeltaPath, metaFilePath)
                #print "4"
                self.PatchLocalFile(localDeltaPath)
                #print "9"
                #self.Cleanup(localDeltaPath)
                del objRemoteSync

                #ACK Part
                #objACKClient = Client()
                #metaACKString = "SYNC ACK:" + self.IPADDRESS
                #objACKClient.SendData(metaACKString)

            else:
                #Send Negative ACK so that client can resend
                print "HASH CHANGED"

        elif command == "DELETE":
            receivedData = command + ":" + metafileName

            if str(metaHash) == self.CalculatedHash(receivedData):
                print "HASH UNCHANGED"
                os.remove("/home/" + getpass.getuser() + "/RemoteSync/" +metafileName)
                print "FILE DELETED"
            else:
                print "HASH CHANGED"

    def Cleanup(self, metaFilePath):
        os.remove(metaFilePath)

    def PatchLocalFile(self, deltaPath):
        finalLocalName = self.GenerateLocalFileName(deltaPath)
        finalLocalFilePath = "/home/"+getpass.getuser()+"/RemoteSync/"+finalLocalName
        finalLocalHiddenFilePath = self.tempPath+"/."+finalLocalName
        #print finalLocalName
        #print finalLocalFilePath
        #print finalLocalHiddenFilePath
        #print deltaPath

        if os.path.exists(finalLocalFilePath):
            os.remove(finalLocalFilePath)

        open(finalLocalFilePath, "w").close


        #if not os.path.exists(finalLocalHiddenFilePath):
            #print "Create a Hidden File"
            #self.CreateEmptyFile(finalLocalHiddenFilePath)

        #Open delta from synced file
        restoredDelta = dill.load(open(deltaPath))

        #Clear a file first
        #file(finalLocalFilePath, 'wb').close

        dst = file(finalLocalFilePath, 'r+')

        librsync.patch(dst, restoredDelta, dst)

        #if os.path.exists(finalLocalHiddenFilePath):
            #self.Cleanup(finalLocalHiddenFilePath)
            #self.CreateEmptyFile(finalLocalHiddenFilePath)
            #print "Cleared the Hidden File"

        self.Cleanup(deltaPath)
        #self.CopyContent(finalLocalFilePath,finalLocalHiddenFilePath)

        dst.close()

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
    if not os.path.isdir("/tmp/RemoteSync"):
        os.makedirs("/tmp/RemoteSync")

    objServer = ThreadedServer()
    objServer.listen()

    #sudo fuser -k 2122/tcp
