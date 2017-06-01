import socket

class Client(object):

    def __init__(self):
        self.PORT = 2122

    def SendData(self, metaData, ipAddress):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ipAddress, self.PORT))
        print "Sending Data: ",metaData, "\tIP Address: ",ipAddress
        sock.send(metaData)
        sock.close()
