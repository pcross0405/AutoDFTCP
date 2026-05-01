import win32wnet

class win32Connection():
    def __init__(
        self,
        username:str = '',
        password:str = '',
        server_path:str = ''
    )->None:
        
        win32wnet.WNetAddConnection2(
            0,
            None,
            server_path,
            UserName=username, #type: ignore
            Password=password  #type: ignore
        ) 
    