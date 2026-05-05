import os
from connection_handler import win32Connection
from typing import Generator
import shutil

class RDrive(win32Connection):
    '''
    Class for interfacing with Research Drive

    Parameters
    ----------
        username : str
            Your NetID@wisc.edu

        password : str
            Your wisc domain password

        sever_path : str
            Path to research drive server
    
    Methods
    -------
        UploadFiles
            Uploads files to specified directory of research drive
    '''

    def __init__(
        self,
        username:str = '',
        password:str = '',
        server_path:str = ''
    ):
        try:
            super().__init__(username, password, server_path)
        
        except:
            pass

        self.server_path = server_path
        self.username = username

    #----------METHODS----------#

    def _GeneratorUpload(
        self,
        file_contents:str,
        destination:str
    ):
        with open(destination, 'w', encoding = 'utf-8') as dst:
            print(file_contents, file = dst)

    def _ListUpload(
        self,
        file:str,
        destination:str
    ):
        shutil.copy(
            src = file,
            dst = destination
        )

    def CheckDir(
        self,
        path:str
    )->bool:

        return os.path.exists(path = path)

    def mkdir(
        self,
        path:str
    ):
        os.mkdir(path = path)
        
    def UploadFiles(
        self,
        dir:str = '',
        files:Generator[tuple[str, str], None, None]|list[str] = ['']
    ):
        '''
        Method for uploading files to a specified directory of research drive

        Parameters
        ----------
            dir : str
                Path to research drive directory to upload to

            files : Generator | str | list
                Files to be upload \n
                Can be read from:
                    - a generator that yields file objects (Generator[TextIOWrapper, None, None])
                    - a list of paths (list[str])
        '''

        upload_dir = self.server_path + '\\' + dir

        if not self.CheckDir(path = upload_dir):
            self.mkdir(path = upload_dir)
        
        if type(files) == list:
            for f in files:
                self._ListUpload(
                    file = f,
                    destination = upload_dir
                )
        
        else:
            for f, file_name in files: 
                print(f'Found file {file_name}')
                self._GeneratorUpload(
                    file_contents = f,
                    destination = upload_dir + '\\' + file_name
                )
    
    def CheckFile(
        self,
        path:str = '',
        file:str = ''
    )->bool:
        check_dir = self.server_path + '\\' + path
        if file in os.listdir(check_dir):
            return True
        
        return False
        
    def AutoCPFetch(
        self
    )->list[str]:
        user_dir = self.username.split('@')[0]
        queue_dir = user_dir + '\\in_queue'
        complete_dir = user_dir + '\\complete'
        full_path = self.server_path + '\\' + queue_dir

        queue = []

        for file in os.listdir(full_path):
            if not self.CheckFile(path=complete_dir, file=file):

                if file.endswith('.in') or file.endswith('.files'):
                    file_name = full_path + '\\' + file.split('.')[0]
                    self.UploadFiles(
                        files = [file_name + '.in', file_name + '.files'],
                        dir = complete_dir 
                    )
                    queue.append(file_name)
                
                elif file.endswith('.cif'):
                    self.UploadFiles(
                        files = [file],
                        dir = complete_dir
                    )
                    queue.append(file)
            
        return queue
