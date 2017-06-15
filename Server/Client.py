import socket
import ssl
import getpass

class Client(object):

    def __init__(self):
        self.PORT = 2122
        self.CERTIFICATE_PATH = '/home/'+ getpass.getuser() +'/Server/SSL_CERT'

    def SendData(self, metaData, ipAddress):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ssl_sock = ssl.wrap_socket(sock,
                                            ca_certs=self.CERTIFICATE_PATH,
                                            cert_reqs=ssl.CERT_REQUIRED )
            self.ssl_sock.connect((ipAddress, self.PORT))
            print "SENDING DATA: ",metaData, "\tIP ADDRESS: ",ipAddress
            self.ssl_sock.send(metaData)
            sock.close()
            self.ssl_sock.close()
        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
