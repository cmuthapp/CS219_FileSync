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
        self.versionHistoryPath = "/home/"+getpass.getuser()+"/Client/Helpers/VersionHistory"
        self.hostList = list()
        self.versionDict = dict()

    def CheckIfExists(self, directory, fileName):
        return os.path.isfile(directory+"/"+fileName)

    def CreateHiddenFile(self, directory, fileName):
        open(directory+ "/" + "." +fileName, "w").close

    #Function to copy file content
    def CopyFile(self, directory, fileName):
        copyfile(self.directoryPath+fileName, directory + "/." +fileName)

    #Function to calculate delta of a file
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

    #Function for calculating SHA1 hash
    def CalculateHash(self, filePath=None):
        sha1Hash = hashlib.sha1()
        with open(filePath, "r") as fileHandle:
            while True:
                fileContentChurn = fileHandle.read(BUF_SIZE).decode('utf8')
                if not fileContentChurn:
                    return sha1Hash.hexdigest()
                    break
                sha1Hash.update(fileContentChurn)

    #Function for copying content of a file
    def CopyContent(self, sourceFileName, destinationFileName):
        with open(self.directoryPath+destinationFileName, 'w+') as output, open(self.directoryPath+sourceFileName, 'r') as input:
            while True:
                data = input.read(100000)
                if data == '':
                    break
                output.write(data)

    # Function for loading version history from version log
    def LoadVersionHistory(self):
        with open(self.versionHistoryPath) as fileHandle:
            for line in fileHandle:
                if line:
                    strippedLine = line.rstrip()
                    self.versionDict[strippedLine.split(':')[0]] = strippedLine.split(':')[1]

    #Function for updating in memory version log
    def UpdateVersionHistory(self,fileName,version):
        self.versionDict[fileName] = version
        print self.versionDict

    #Function for saving the version log on disk
    def WriteVersionLog(self):
        fileHandle = open(self.versionHistoryPath, 'w')
        for fileName, version in self.versionDict.iteritems():
            fileHandle.write(fileName+":"+version+"\n")
        fileHandle.close()
        print self.versionDict

    #Remove an element from in memory version log
    def RemoveVersionLog(self,fileName):
        if fileName in self.versionDict:
            del self.versionDict[fileName]

    #Fetch version from in memory version log
    def GetFileVersion(self, fileName):
        return self.versionDict[fileName]
