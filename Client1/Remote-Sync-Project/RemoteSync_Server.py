import socket
import threading
import hashlib

class ThreadedServer(object):
    def __init__(self):
        self.IPADDRESS = "192.168.1.13"
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
        metaDestIP = metaList[0]
        metafilePath = metaList[1]
        metaSHA1 = metaList[2]

        receivedData = metaDestIP + ":" + metafilePath

        if str(metaSHA1) == self.CalculatedHash(receivedData):
            print "Hash Matched"
            #self.BroadcastMetaData(metaData)
            #Send ACK
        else:
            #Send Negative ACK so that client can resend
            print "Data Changed"

    def CalculatedHash(self, receivedData):
        hashObject = hashlib.sha1(receivedData)
        hexDigest = hashObject.hexdigest()
        return str(hexDigest)

if __name__ == "__main__":
    objServer = ThreadedServer()
    objServer.listen()
