import socket
import threading
import hashlib
import os

from RemoteSync_Client import Client

class ThreadedServer(object):
    def __init__(self):
        self.IPADDRESS = "192.168.1.15"
        self.PORT = 2122
        self.hostList = self.FetchHostList()
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
                    self.ProcessMetaData(data, address[0])
                else:
                    raise error('Client Disconnected')
            except:
                client.close()
                return False

    def ProcessMetaData(self, metaData, targetIP):
        metaList = metaData.split(":")
        if len(metaList) == 4:
            command = metaList[0]
            metaDestIP = metaList[1]
            metafilePath = metaList[2]
            metaSHA1 = metaList[3]
        if len(metaList) == 3:
            command = metaList[0]
            fileName = metaList[1]
            metaSHA1 = metaList[2]

        if command == "PUSH":
            receivedData = command + ":" + metaDestIP + ":" + metafilePath

            if str(metaSHA1) == self.CalculatedHash(receivedData):
                print "Data Unchanged - PUSH"
                self.BroadcastMetaData(metafilePath, targetIP)
                #Send ACK
            else:
                #Send Negative ACK so that client can resend
                print "Data Changed"
        if command == "GET LOCK":
            receivedData = command + ":" + fileName
            objClient = Client()

            if str(metaSHA1) == self.CalculatedHash(receivedData):
                print "Data Unchanged - GET LOCK"
                print "File Name: ",fileName
                print "Target IP: ",targetIP
                print "Hash: ",metaSHA1
                if self.CheckLock(fileName, targetIP, command):
                    metaGrantString = "GRANT:" + fileName
                    metaGrantString = metaGrantString + ":" + self.CalculatedHash(metaGrantString)
                    print metaGrantString
                    objClient.SendData(metaGrantString, targetIP)
                else:
                    metaGrantString = "NO GRANT:" + fileName
                    metaGrantString = ":" + self.CalculatedHash(metaGrantString)
                    objClient.SendData(metaGrantString, targetIP)
            else:
                #Send Negative ACK so that client can resend
                print "Data Changed"

    def CheckLock(self, fileName, ipAddress, command):
        print "File Name: ",fileName
        print "IP Address: ",ipAddress
        print "Command: ",command
        myfile = open('SyncedFiles', 'r')
        fileList = list()
        for line in myfile:
            if line:
                fileList.append(line.read().replace('\n', ''))
        myfile.close()

        if command == "GET LOCK":
            print "File Name (GET LOCK): ",fileName
            print "IP Address (GET LOCK): ",ipAddress
            print "Command (GET LOCK): ",command
            counter = 0
            for files in fileList:
                if fileName in files:
                    tempList = files.split(":")
                    syncedFile = tempList[0]
                    ip = tempList[1]
                    if not ip == "NONE":
                        #Deny Access to file
                        return False
                    else:
                        #Replace line in file
                        files = syncedFile + ":" + ipAddress
                        fileList[counter] = files
                        myfile = open('SyncedFiles', 'w')
                        for list_element in fileList:
                            myfile.write(list_element+"\n")
                        myfile.close()
                        return True
                counter = counter + 1

            myfile = open('SyncedFiles', 'a')
            myfile.write(fileName + ":" + str(ipAddress))
            myfile.close()
            return True
        elif command == "RELEASE LOCK":
            print "File Name (RELEASE LOCK): ",fileName
            print "IP Address (RELEASE LOCK): ",ipAddress
            print "Command (RELEASE LOCK): ",command
            counter = 0
            for files in fileList:
                if fileName in files:
                    tempList = files.split(":")
                    syncedFile = tempList[0]
                    ip = tempList[1]
                    fileList[counter] = syncedFile + ":" + "NONE"
                counter = counter + 1
            return True

    def write_to_file(self, tempList):
        for elements in tempList:
            fileHandler.write(elements + "\n")

    def BroadcastMetaData(self, metaData, targetIP):
        completeTargetInfo = self.GetTargetInfo(targetIP)
        metaData = "PUSH:" + metaData + ":" + completeTargetInfo
        print "Meta Data: ",metaData

        finalMetaData = metaData + ":" + self.CalculatedHash(metaData)
        print "Final MetaData: ",finalMetaData
        objClient = Client()
        for hostElement in self.hostList:
            sockAddress = finalMetaData.split(":")[2]
            if not sockAddress in hostElement:
                objClient.SendData(finalMetaData, hostElement.split(":")[0])
                print "Data Sent"

    def GetTargetInfo(self, targetIP):
        for element in self.hostList:
            if targetIP in element:
                return element

    def CalculatedHash(self, receivedData):
        hashObject = hashlib.sha1(receivedData)
        hexDigest = hashObject.hexdigest()
        return str(hexDigest)

    def FetchHostList(self):
        with open(os.getcwd()+"/Hosts") as fileHandle:
            content = fileHandle.readlines()

        return [x.strip() for x in content]

if __name__ == "__main__":
    objServer = ThreadedServer()
    objServer.listen()
