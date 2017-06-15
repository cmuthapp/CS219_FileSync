import socket
import threading
import hashlib
import os
import datetime
import getpass
import ssl

from Client import Client

class ThreadedServer(object):
    def __init__(self):
        self.IPADDRESS = "192.168.1.15"
        self.PORT = 2122
        self.hostList = self.FetchHostList()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.IPADDRESS, self.PORT))
        self.CERTIFICATE_PATH = '/home/'+ getpass.getuser() +'/Server/SSL_CERT'
        self.KEY_PATH = '/home/'+ getpass.getuser() +'/Server/SSL_KEY'

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
                    self.ProcessMetaData(data, address[0], self.connstream)
                else:
                    raise error('Client Disconnected')
            except:
                client.close()
                return False

        self.connstream.close()
        client.close()

    def ProcessMetaData(self, metaData, targetIP, clientHandler):
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
                print "PUSH META STRING RECEIVED"
                print "PUSH: HASH UNCHANGED"
                self.BroadcastMetaData(metafilePath, targetIP)
                #Send ACK
            else:
                #Send Negative ACK so that client can resend
                print "PUSH: HASH CHANGED"
            return
        if command == "GET LOCK":
            receivedData = command + ":" + fileName

            if str(metaSHA1) == self.CalculatedHash(receivedData):
                print "LOCK REQUESTED"
                print "GET LOCK: HASH UNCHANGED"
                #print "FILE NAME: ",fileName
                #print "TARGET IP: ",targetIP
                #print "HASH: ",metaSHA1
                if self.CheckLock(fileName, targetIP, command):
                    metaGrantString = "GRANT:" + fileName
                    metaGrantString = metaGrantString + ":" + self.CalculatedHash(metaGrantString)
                    #print "GRANT: ",metaGrantString
                    print "LOCK GRANTED"
                    self.WriteLog("GRANT LOCK:"+targetIP+":"+fileName+":"+str(datetime.datetime.utcnow()))
                    clientHandler.send(metaGrantString)
                else:
                    metaGrantString = "NO GRANT:" + fileName
                    metaGrantString = metaGrantString + ":" + self.CalculatedHash(metaGrantString)
                    #print "NO GRANT: ",metaGrantString
                    print "LOCK NOT GRANTED"
                    clientHandler.send(metaGrantString)
            else:
                #Send Negative ACK so that client can resend
                print "GET LOCK:HASH CHANGED"
                return

        if command == "RELEASE LOCK":
            receivedData = command + ":" + fileName

            if str(metaSHA1) == self.CalculatedHash(receivedData):
                print "LOCK RELEASED"
                print "RELEASE LOCK: HASH UNCHANGED"
                #print "File Name: ",fileName
                #print "Target IP: ",targetIP
                #print "Hash: ",metaSHA1
                if self.CheckLock(fileName, targetIP, command):
                    metaGrantString = "GRANT:" + fileName
                    metaGrantString = metaGrantString + ":" + self.CalculatedHash(metaGrantString)
                    #print "GRANT: ",metaGrantString
                    print "RELEASE LOCK ACK"
                    self.WriteLog("RELEASE LOCK:"+targetIP+":"+fileName+":"+str(datetime.datetime.utcnow()))
                    clientHandler.send(metaGrantString)
            else:
                #Send Negative ACK so that client can resend
                print "RELEASE LOCK:HASH CHANGED"
                return

        if command == "DELETE":
            receivedData = command + ":" + fileName

            if str(metaSHA1) == self.CalculatedHash(receivedData):
                print "DELETE REQUESTED"
                print "DELETE FILE: HASH UNCHANGED"
                self.BroadcastDeleteMetaData(metaData, targetIP)
                self.DeleteFileInformation(fileName)
                print "DELETE COMPLETED"
                clientHandler.send("ACK:"+self.CalculatedHash("ACK"))
            else:
                print "DELETE FILE: HASH CHANGED"

    def WriteLog(self, content):
        #print "LOG: "+content
        with open("TimeLog", "a") as myfile:
            myfile.write(content+"\n")

    def DeleteFileInformation(self, fileName):
        try:
            myfile = open('SyncedFiles', 'r')
            fileList = list()
            for line in myfile:
                fileList.append(line.replace('\n', ''))
            myfile.close()
        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
            sys.exit(0)

        for elements in fileList:
            if fileName in elements:
                fileList.remove(elements)

        fileList = self.CleanList(fileList)

        open('SyncedFiles', 'w').close()

        myfile = open('SyncedFiles', 'w')
        for list_element in fileList:
            myfile.write(list_element+"\n")
        myfile.close()

    def CleanList(self, fileList):
        for elements in fileList:
            if elements == "\n":
                fileList.remove(elements)
            elif elements == "":
                fileList.remove(elements)

        return fileList


    def CheckLock(self, fileName, ipAddress, command):
        #print "File Name: ",fileName
        #print "IP Address: ",ipAddress
        #print "Command: ",command
        try:
            myfile = open('SyncedFiles', 'r')
            fileList = list()
            for line in myfile:
                fileList.append(line.replace('\n', ''))
            myfile.close()

            fileList = self.CleanList(fileList)
        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
            sys.exit(0)

        if command == "GET LOCK":
            #print "File Name (GET LOCK): ",fileName
            #print "IP Address (GET LOCK): ",ipAddress
            #print "Command (GET LOCK): ",command
            counter = 0
            for files in fileList:
                if fileName in files:
                    tempList = files.split(":")
                    syncedFile = tempList[0]
                    ip = tempList[1]
                    if ip == ipAddress and not ip == "NONE":
                        #print "LOCK: Address Match"
                        return True
                    elif not ip == ipAddress and not ip == "NONE":
                        #Deny Access to file
                        #print "LOCK: Address don't match"
                        return False
                    elif ip == "NONE":
                        #Replace line in file
                        files = syncedFile + ":" + ipAddress
                        fileList[counter] = files
                        myfile = open('SyncedFiles', 'w')
                        for list_element in fileList:
                            myfile.write(list_element+"\n")
                        myfile.close()
                        #print "LOCK: Granted"
                        return True
                counter = counter + 1

            myfile = open('SyncedFiles', 'a')
            myfile.write(fileName + ":" + str(ipAddress) + "\n")
            myfile.close()
            return True
        elif command == "RELEASE LOCK":
            #print "File Name (RELEASE LOCK): ",fileName
            #print "IP Address (RELEASE LOCK): ",ipAddress
            #print "Command (RELEASE LOCK): ",command
            counter = 0
            for files in fileList:
                #print "Test: ",files
                if fileName in files:
                    tempList = files.split(":")
                    syncedFile = tempList[0]
                    ip = tempList[1]
                    fileList[counter] = syncedFile + ":" + "NONE"
                counter = counter + 1

            myfile = open('SyncedFiles', 'w')
            for list_element in fileList:
                myfile.write(list_element+"\n")
            myfile.close()
            return True

    def write_to_file(self, tempList):
        for elements in tempList:
            fileHandler.write(elements + "\n")

    def BroadcastMetaData(self, metaData, targetIP):
        completeTargetInfo = self.GetTargetInfo(targetIP)
        metaData = "PUSH:" + metaData + ":" + completeTargetInfo
        #print "Meta Data: ",metaData

        finalMetaData = metaData + ":" + self.CalculatedHash(metaData)
        #print "Final MetaData: ",finalMetaData
        objClient = Client()
        for hostElement in self.hostList:
            sockAddress = finalMetaData.split(":")[2]
            if not sockAddress in hostElement:
                objClient.SendData(finalMetaData, hostElement.split(":")[0])
                print "META STRING SENT TO ",hostElement.split(":")[0]

    def BroadcastDeleteMetaData(self, metaData, targetIP):
        objClient = Client()
        for hostElement in self.hostList:
            if not targetIP in hostElement:
                objClient.SendData(metaData, hostElement.split(":")[0])
                print "META DELETE STRING SENT TO ",hostElement.split(":")[0]

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
