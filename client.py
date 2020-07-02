import socket
import os
import getpass
import re


class FTPClient:
    def __init__(self, addr='0.0.0.0'):
        self.addr = addr  # 连接服务器的IP地址
        self.port = 21  # 连接服务器的命令端口
        self.Connected = False  # 服务器连接状态
        self.debug = False
        self.user = False  # 服务器用户登陆状态
        self.silent = False  # 客户端的各种状态
        if(addr != '0.0.0.0'):
            self.open(addr)  # 可直接初始化时建立连接

# 命令传送函数
    def send(self, message):
        try:
            if(self.debug):
                print('--> '+message)
            message = bytes(message+'\r\n', encoding='ascii')
            self.sock.send(message)
        except:
            return

# 命令接收函数
    def recv(self):
        try:
            data = self.sock.recv(1024).decode('ascii').replace('\r\n', '')
            if(not self.silent):
                print(data)
            if(data[0] == '3' or data[0] == '4' or data[0] == '5'):
                raise Exception('connection error')
            return data
        except:
            pass

# 用户登陆函数，530为登陆失败的返回码
    def login(self):
        try:
            user = input('User ('+self.addr+':)')
            self.send('USER '+user)
            self.recv()
            passwd = getpass.getpass('Password:')  # 输入隐藏比密码
            self.send('PASS '+passwd)
            if(self.recv()[0:3] != '530'):
                self.user = True
        except:
            print('login failed')

# 连接远程服务器
    def open(self, addr):
        try:
            socket.inet_aton(addr)  # 检测IP合法性
        except:
            print('invalid ip')
            return
        try:
            if(self.Connected):
                print('already connected to '+self.addr)  # 判断当前连接状态
                return
            self.addr = addr
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self.sock.connect((self.addr, self.port))  # 建立连接
            self.Connected = True
            self.recv()
        except:
            print('Connect refused')
            return
        self.send('OPTS UTF8 ON')
        self.recv()
        self.login()  # 默认连接建立时登陆

# 断开连接函数
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

# FTP使用主动模式，发送PASV命令
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

# 文件上传函数
    def put(self, filename):
        try:
            if(os.path.exists(os.getcwd()+'/'+filename) is False):
                print('file not exits')  # 检查本地文件是否存在
                return
            dataAddr, dataport = self.PASV()
            datasock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            datasock.connect((dataAddr, dataport))  # 建立数据连接
            self.send('STOR '+filename)
            self.recv()
            f = open(os.getcwd()+'/'+filename, 'rb')
            while True:  # 文件分段发送
                data = f.read(1024)
                if(not data):
                    break
                datasock.send(data)
            datasock.close()  # 关闭数据连接
            self.recv()
        except:
            print('Transfer failed')

# 检查远程服务器文件是否存在
    def checkfileexit(self, filename):
        try:
            self.silent = True
            files = self.LS().split('\r\n')  # 通过LS命令读取远程目录的文件项
            flag = False
            for item in files:
                if(item.find(filename) != -1 and item[0] != 'd'):
                    # 判断是否有同名文件
                    flag = True
                    break
            self.silent = False
            if(not flag):
                print('file not exits')
            return flag
        except:
            print('unknown error')

# 检查远程服务器文件夹是否存在
    def checkdirexit(self, filename):
        try:
            self.silent = True
            files = self.LS().split('\r\n')  # 通过LS命令读取远程目录的文件项
            flag = False
            for item in files:
                if(item.find(filename) != -1 and item[0] == 'd'):
                    # 判断是否有同名文件夹
                    flag = True
                    break
            self.silent = False
            if(not flag):
                print('directory not exits')
            return flag
        except:
            print('unknown error')

# 下载函数，获得远程服务器的文件
    def get(self, filename):
        # 判断文件是否存在
        if(not self.checkfileexit(filename)):
            return
        try:
            dataAddr, dataport = self.PASV()
            datasock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            datasock.connect((dataAddr, dataport))  # 建立数据连接
            self.send('RETR '+filename)
            filesize = int(re.findall(
                r'[(](.*)[)]', self.recv())[0].split(' ')[0])
            buffersize = 1024
            f = open(filename, 'wb')
            while(filesize > 0):  # 分段接收数据
                buffer = datasock.recv(buffersize)
                f.write(buffer)
                filesize = filesize-buffersize
            f.close()
            datasock.close()  # 关闭数据连接
            self.recv()
        except:
            print('Transfer failed')

# 获取远程服务器的文件列表 文件列表通过数据通道接收
    def LS(self):
        try:
            dataAddr, dataport = self.PASV()
            datasock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            datasock.connect((dataAddr, dataport))  # 数据连接建立
            self.send('LIST')
            self.recv()
            buffersize = 1024
            buffer = datasock.recv(buffersize).decode('ascii')  # 接收数据
            datasock.close()
            if(not self.silent):
                print(buffer)
            self.recv()
            return buffer
        except:
            print('unknown error')

    def cmd(self):
        cmd = input('ftp>')
        if(cmd == 'help'):  # 帮助命令
            print(
                '''help     get help
open     open a remote connection args:<IP>
discon     disconnect the remote connection
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
        elif(cmd == 'quit'):  # 关闭FTP客户端
            if(self.Connected):
                self.disconnect()
            quit()
        elif(cmd[0:4] == 'open'):  # 建立远程连接
            self.open(cmd.split(' ')[1])
        elif(cmd == 'discon'):  # 断开远程连接
            self.disconnect()
        elif(cmd == 'login'):  # 登陆远程服务器
            self.login()
        elif(cmd == 'status'):  # 查看客户端状态
            print('connected: '+str(self.Connected), end=' ')
            print('login: '+str(self.user))
        else:
            if(not self.user):
                print('please login first')
            else:
                if(cmd == 'lcd'):  # 获取当前的本地路径
                    print(os.getcwd())
                elif(cmd[0:3] == 'put'):  # 发送文件
                    self.put(cmd.split(' ')[1])
                elif(cmd[0:3] == 'get'):  # 下载文件
                    self.get(cmd.split(' ')[1])
                elif(cmd == 'pwd'):  # 获取服务器的路径
                    self.send('XPWD')
                    self.recv()
                elif(cmd[0:5] == 'mkdir'):  # 创建文件夹
                    self.send('XMKD '+cmd.split(' ')[1])
                    self.recv()
                elif(cmd[0:2] == 'cd'):  # 打开文件夹
                    self.send('CWD '+cmd.split(' ')[1])
                    self.recv()
                elif(cmd == 'ls'):  # 获取文件列表
                    self.LS()
                elif(cmd[0:6] == 'delete'):  # 删除文件
                    if(self.checkfileexit(cmd.split(' ')[1])):
                        self.send('DELE '+cmd.split(' ')[1])
                        self.recv()
                elif(cmd[0:5] == 'rmdir'):  # 删除文件夹
                    if(self.checkdirexit(cmd.split(' ')[1])):
                        self.send('RMD '+cmd.split(' ')[1])
                        self.recv()
                else:
                    print('command not find\nsupport command see <help>')


if(__name__ == '__main__'):
    clnt = FTPClient()
    while True:
        clnt.cmd()
