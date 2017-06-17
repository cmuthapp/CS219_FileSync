# CS219_FileSync
Simple File Sync 

## Steps to setup the system

1. Have atleast 3 systems that can communicate with each other via SSH.
2. One of them is going to be the Control Server and the remaining two clients
3. Open the port 2122 in all the Systems
4. Record the SSH username and password for the client systems.
5. Copy the *Server* folder to one of the systems which will serve as Control Server. Edit the *Hosts* file with the ip of the client systems and their usernames and passwords. (Example- HOST_IP:USERNAME:PASSWORD)
6. Run the *Server.py* in the Control Server.
7. Copy the *Client{1}* folder in all of the clients. {1} can be any number
8. Run *Server.py* and *Client.py* from the Client folder in the system on the system you are currently making changes on.
9. Run *ONLY* *Server.py* from the Client folder in the systems that are not making any changes.

*Note:* You will need to change the IP Addresses in the init part of Server and Client files. All install missing libraries according to the command given as comment in the code. For generating new key and certificate, command is given in the README of the Server directory.
