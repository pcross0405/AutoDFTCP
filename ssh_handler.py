import fabric as fb
import paramiko as pm

class FabricLike():
    def __init__(
        self,
        transport:pm.Transport
    ):
        self.transport = transport

    def run(
        self,
        command:str,
        nbytes:int = 1024
    ):
        client = self.transport.open_session()
        client.exec_command(command = command)
        return client.recv(nbytes = nbytes).decode('utf-8').strip()

class SSH():
    def __init__(
        self, 
        host:str = '',
        user:str = '',
    ):
        self.fabric = False
        self.pm = False
        self.host = host
        self.user = user

        if host:
            try:
                print(f'Attempting to connect to server: {self.host} via Fabric')

                self.client = fb.Connection(
                    host = self.host,
                    user = user
                )

                #if self.client.is_connected:
                print(f'User: {self.client.run("echo $USER")} successfully connected')
                self.fabric = True

            except:
                print('Fabric connection failed, attempting to establish SSH Client with Paramiko')

                try:
                    transport = pm.Transport(host)
                    transport.connect(username=user)
                    transport.auth_interactive_dumb(username=user)
                
                except:
                    print('Paramiko SSH Client failed.')
                    print('Attempt manual input')

                    try:
                        password = input(f'Provide password for {self.host}: ')
                        transport = pm.Transport(host)
                        transport.connect(username=user,password=password)
                        if self.host.startswith('spark'):
                            transport.auth_interactive_dumb(username=user)

                    except:
                        print('All SSH attempts failed, exiting')
                        raise SystemExit
                    
                if transport.is_authenticated:
                    print('SSH Client established')

                    self.client = FabricLike(transport = transport)

                    print(f'User: {self.client.run("echo $USER")} successfully connected')
                    self.pm = True

    #--------METHODS--------#

    # method for getting hostname
    @property
    def hostname(
        self
    ):
        return self.client.run('hostname')

    def check_dir(
        self,
        path:str
    )->int:
        if self.pm:
            channel = self.client.transport.open_session() #type: ignore
            channel.exec_command(f'cd {path}')
            return channel.recv_exit_status()
        return -1

    def mkdir(
        self,
        path:str
    ):
        self.client.run(f'mkdir {path}')

    def ls(
        self,
        path:str = '.'
    )->list:
        dirs = self.client.run(f'ls {path}').replace('\n', ' ')
        dirs = dirs.split(' ')
        return [d for d in dirs if d != '']
    
    def cmd_string(
        self,
        commands:list
    ):
        cmds = ';'.join(commands)
        return self.client.run(cmds)
    
    def cat(
        self,
        path:str
    )->str:
        if self.pm:
            file_contents = self.client.run(f'cat {path}', nbytes = 8192)
        else:
            file_contents = self.client.run(f'cat {path}')
        return file_contents

    def smb(
        self,
        remote_path:str='AutoCP',
        local_path:str='',
        password:str=''
    ):
        self.cmd_string(
            commands = [
                "export LD_LIBRARY_PATH=''",
                f"smbclient -U {self.user}@ad.wisc.edu%{password} //research.drive.wisc.edu/dcfredrickso -c 'put {local_path} {remote_path}'"
            ]
        )
        