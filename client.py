import socket
import os
import getpass
import random
import re


class FTPClient:
    def __init__(self, addr='0.0.0.0'):
        self.addr = addr
        self.port = 21
        self.Connected = False
        self.debug = False
        self.user = False
        self.slient = False
        if(addr != '0.0.0.0'):
            self.open(addr)

    def send(self, message):
        try:
            if(self.debug):
                print('--> '+message)
            message = bytes(message+'\r\n', encoding='ascii')
            self.sock.send(message)
        except:
            return

    def recv(self):
        try:
            data = self.sock.recv(1024).decode('ascii').replace('\r\n', '')
            if(not self.slient):
                print(data)
            if(data[0] == '3' or data[0] == '4' or data[0] == '5'):
                raise Exception('connection error')
            return data
        except:
            pass

    def login(self):
        try:
            user = input('User ('+self.addr+':)')
            self.send('USER '+user)
            self.recv()
            passwd = getpass.getpass('Password:')
            self.send('PASS '+passwd)
            if(self.recv()[0:3] != '530'):
                self.user = True
        except:
            print('login failed')

    def open(self, addr):
        try:
            socket.inet_aton(addr)
        except:
            print('invalid ip')
            return
        try:
            if(self.Connected):
                print('already connected to '+self.addr)
                return
            self.addr = addr
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self.sock.connect((self.addr, self.port))
            self.Connected = True
            self.recv()
        except:
            print('Connect refused')
        self.send('OPTS UTF8 ON')
        self.recv()
        self.login()

    def disconnect(self):
        try:
            self.send('quit')
            self.recv()
        except:
            print('disconnect failed. maybe not connect yet')
            return
        self.Connected = False
        self.user = False
        self.sock.close()

    def PASV(self):
        try:
            self.send('PASV')
            recv = self.recv()
            if(recv[0] == '4' or recv[0] == '5'):
                raise Exception('PASV error')
            tmp = re.findall(r'[(](.*)[)]', recv)[0]
            tmp = tmp.split(',')
            dataAddr = tmp[0]+'.'+tmp[1]+'.'+tmp[2]+'.'+tmp[3]
            dataport = int(tmp[4])*256+int(tmp[5])
            return dataAddr, dataport
        except Exception as e:
            print(e)

    def put(self, filename):
        try:
            if(os.path.exists(os.getcwd()+'/'+filename) == False):
                print('file not exits')
                return
            dataAddr, dataport = self.PASV()
            datasock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            datasock.connect((dataAddr, dataport))
            self.send('STOR '+filename)
            self.recv()
            f = open(os.getcwd()+'/'+filename, 'rb')
            while True:
                data = f.read(1024)
                if(not data):
                    break
                datasock.send(data)
            datasock.close()
            self.recv()
        except:
            print('Transfer failed')

    def checkfileexit(self, filename):
        try:
            self.slient = True
            files = self.LS().split('\r\n')
            flag = False
            for item in files:
                if(item.find(filename) != -1 and item[0] != 'd'):
                    flag = True
                    break
            self.slient = False
            if(not flag):
                print('file not exits')
            return flag
        except:
            print('unknown error')

    def checkdirexit(self, filename):
        try:
            self.slient = True
            files = self.LS().split('\r\n')
            flag = False
            for item in files:
                if(item.find(filename) != -1 and item[0] == 'd'):
                    flag = True
                    break
            self.slient = False
            if(not flag):
                print('directory not exits')
            return flag
        except:
            print('unknown error')

    def get(self, filename):
        if(not self.checkfileexit(filename)):
            return
        try:
            dataAddr, dataport = self.PASV()
            datasock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            datasock.connect((dataAddr, dataport))
            self.send('RETR '+filename)
            filesize = int(re.findall(
                r'[(](.*)[)]', self.recv())[0].split(' ')[0])
            buffersize = 1024
            f = open(filename, 'wb')
            while(filesize > 0):
                buffer = datasock.recv(buffersize)
                f.write(buffer)
                filesize = filesize-buffersize
            f.close()
            datasock.close()
            self.recv()
        except:
            print('Transfer failed')

    def LS(self):
        try:
            dataAddr, dataport = self.PASV()
            datasock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            datasock.connect((dataAddr, dataport))
            self.send('LIST')
            self.recv()
            buffersize = 1024
            buffer = datasock.recv(buffersize).decode('ascii')
            datasock.close()
            if(not self.slient):
                print(buffer)
            self.recv()
            return buffer
        except:
            print('unknown error')

    def cmd(self):
        cmd = input('ftp>')
        if(cmd == 'help'):
            print(
                '''help     get help
open     open a remote connection args:<IP>
dcon     disconnect the remote connection
login    login remote system
status   client status
quit     close connection
pwd      get remote working directory
lcd      get local working directory
put      upload file
get      download file
mkdir    create directory 
rmdir    delete directory
delete   delete file
ls       list files'''
            )
        elif(cmd == 'quit'):
            if(self.Connected):
                self.disconnect()
            quit()
        elif(cmd[0:4] == 'open'):
            self.open(cmd.split(' ')[1])
        elif(cmd == 'discon'):
            self.disconnect()
        elif(cmd == 'login'):
            self.login()
        elif(cmd == 'status'):
            print('connected: '+str(self.Connected), end=' ')
            print('login: '+str(self.user))
        else:
            if(not self.user):
                print('please login first')
            else:
                if(cmd == 'lcd'):
                    print(os.getcwd())
                elif(cmd[0:3] == 'put'):
                    self.put(cmd.split(' ')[1])
                elif(cmd[0:3] == 'get'):
                    self.get(cmd.split(' ')[1])
                elif(cmd == 'pwd'):
                    self.send('XPWD')
                    self.recv()
                elif(cmd[0:5] == 'mkdir'):
                    self.send('XMKD '+cmd.split(' ')[1])
                    self.recv()
                elif(cmd[0:2] == 'cd'):
                    self.send('CWD '+cmd.split(' ')[1])
                    self.recv()
                elif(cmd == 'ls'):
                    self.LS()
                elif(cmd[0:6] == 'delete'):
                    if(self.checkfileexit(cmd.split(' ')[1])):
                        self.send('DELE '+cmd.split(' ')[1])
                        self.recv()
                elif(cmd[0:5] == 'rmdir'):
                    if(self.checkdirexit(cmd.split(' ')[1])):
                        self.send('RMD '+cmd.split(' ')[1])
                        self.recv()
                else:
                    print('command not find\nsupport command see <help>')


if(__name__ == '__main__'):
    clnt = FTPClient()
    while True:
        clnt.cmd()
