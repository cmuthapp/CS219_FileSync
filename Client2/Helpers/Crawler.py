import os
import hashlib
import re
import dill
import librsync
import getpass
from shutil import copyfile #copyfile(src, dst)

BUF_SIZE = 65536 #Change when needed

class Crawler:

    def __init__(self):
        self.directoryPath = "/home/"+getpass.getuser()+"/RemoteSync/"
        self.hostFilePath = os.getcwd()+"/Helpers/hosts"
        self.hostList = list()

    def CheckIfExists(self, directory, fileName):
        return os.path.isfile(directory+"/"+fileName)

    def CreateHiddenFile(self, directory, fileName):
        open(directory+ "/" + "." +fileName, "w").close

    def CopyFile(self, directory, fileName):
        copyfile(self.directoryPath+fileName, directory + "/." +fileName)

    def CalculateDelta(self, directory, fileName):

        if os.path.exists(directory+ "/" +".Delta_"+fileName):
            os.remove(directory+ "/" +".Delta_"+fileName)

        # The destination file.
        src = file(self.directoryPath+fileName, 'rb')
        # The source file.
        dst = file(directory+ "/" +"."+fileName, 'rb')
        # Step 1: prepare signature of the destination file
        signature = librsync.signature(dst)

        # Step 2: prepare a delta of the source file
        delta = librsync.delta(src, signature)

        #Save delta in a file
        dill.dump(delta, open(directory+ "/" +".Delta_"+fileName, "w"))

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
