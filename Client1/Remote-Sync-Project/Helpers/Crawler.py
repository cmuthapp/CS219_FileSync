import os
import hashlib
import re
import dill
import librsync
import getpass

BUF_SIZE = 65536 #Change when needed

class Crawler:

    def __init__(self):
        self.directoryPath = "/home/"+getpass.getuser()+"/RemoteSync/"
        self.hostFilePath = os.getcwd()+"/Helpers/hosts"
        self.hostList = list()

    def CheckIfExists(self, fileName):
        return os.path.isfile(self.directoryPath+fileName)

    def CreateHiddenFile(self, fileName):
        open(self.directoryPath+"."+fileName, "w").close

    def CalculateDelta(self, fileName):

        if os.path.exists(self.directoryPath+".Delta_"+fileName):
            os.remove(self.directoryPath+".Delta_"+fileName)

        # The destination file.
        src = file(self.directoryPath+fileName, 'rb')
        # The source file.
        dst = file(self.directoryPath+"."+fileName, 'rb')
        # Step 1: prepare signature of the destination file
        signature = librsync.signature(dst)

        # Step 2: prepare a delta of the source file
        delta = librsync.delta(src, signature)
        
        #Clean the Delta File
        open(self.directoryPath+".Delta_"+fileName, "wb").close

        #Save delta in a file
        dill.dump(delta, open(self.directoryPath+".Delta_"+fileName, "wb"))
        del delta

    def CalculateHash(self, filePath=None):
        sha1Hash = hashlib.sha1()
        with open(filePath, "r") as fileHandle:
            while True:
                fileContentChurn = fileHandle.read(BUF_SIZE).decode('utf8')
                if not fileContentChurn:
                    return sha1Hash.hexdigest()
                    break
                sha1Hash.update(fileContentChurn)

    def CopyContent(self, sourceFileName, destinationFileName):
        #print "Source File: ",sourceFileName
        #print "Destination File: ",destinationFileName
        with open(self.directoryPath+destinationFileName, 'w+') as output, open(self.directoryPath+sourceFileName, 'r') as input:
            while True:
                data = input.read(100000)
                if data == '':
                    break
                output.write(data)

    '''def FetchHostList(self):
        with open(self.hostFilePath) as fileHandle:
            content = fileHandle.readlines()

        self.hostList = [x.strip() for x in content]'''
