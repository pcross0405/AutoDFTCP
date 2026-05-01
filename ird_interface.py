import os
from zipfile import ZipFile
from connection_handler import win32Connection
from typing import Generator

class IRD(win32Connection):
    '''
    Class for interfacing with Intermetallic Reactivity Database

    Parameters
    ----------
        username : str
            Your NetID@wisc.edu

        password : str
            Your wisc domain password

        sever_path : str
            Path to IRD server
    
    Methods
    -------
        FetchFiles
            Grabs files from IRD
    '''

    def __init__(
        self, 
        username:str = '', 
        password:str = '',
        server_path:str = ''
    ):
        
        super().__init__(username, password, server_path)
        self.sever_path = server_path

    #----------METHODS----------#

    def FetchFiles(
        self,
        extensions:list = [],
    )->Generator[tuple[str, str], None, None]:
        '''
        Generator for grabbing all files with specified extensions from IRD

        Parameters
        ----------
            extensions : list
                List of all file extensions to fetch from IRD

        Returns
        -------
            Generator[[tuple[TextIOWrapper, str], None, None]]
                Yields open file stream and file name
        '''

        fetch_path = self.sever_path + r'\private\Zip'
        logIRD = open(file = 'IRD_Fetch_log.txt', mode = 'w')

        # loop over all zip files in IRD server
        for zdir in os.listdir(fetch_path):
            path2zip = fetch_path + '\\' + zdir
            with ZipFile(path2zip) as z:
                for f in z.namelist():
                    # check for all files within each zip folder for files with matching extensions
                    if any([f.endswith(ext) for ext in extensions]):
                        print(path2zip + '\\' + f, file = logIRD) 
                        try:
                            # read in file and yield it for copying
                            file = z.read(f).decode('utf-8')
                            yield file, f.split('/')[-1]
                        except Exception as e:
                            print(f'File found at {f} is problematic')
                            print(f'Exception message: {e}')
                            print(f'File found at {f} is problematic', file = logIRD) 
                            print(f'Exception message: {e}', file = logIRD) 

        logIRD.close()

    def RemoveFiles(
        self,
        extensions:list = [],
        private:bool = False
    ):
        '''
        Method for removing all files with specified extensions from IRD

        Parameters
        ----------
            extensions : list
                List of all file extensions to remove from IRD
            
            private : bool
                If True, remove files from private IRD server \n
                Default is False, removes files from public IRD server
        '''

        rm_path = self.sever_path + r'\public\Zip' if not private else self.sever_path + r'\private\Zip'
        logIRD = open(file = 'IRD_Remove_log.txt', mode = 'w')

        # loop over all zip files in IRD server
        for zdir in os.listdir(rm_path):
            path2zip = rm_path + '\\' + zdir
            # open original zip file
            with ZipFile(path2zip) as z:
                # make new temporary zip file as there is no native remove operation for zip files in python
                with ZipFile(path2zip + '_temp', 'w') as znew:
                    for f_info in z.infolist():
                        # copy all files that do not have the extension to be removed
                        if not any([f_info.filename.endswith(ext) for ext in extensions]):
                            data = z.read(f_info.filename)
                            znew.writestr(f_info, data)
                        else:
                            print(path2zip + '\\' + f_info.filename, file = logIRD)        
            # remove original zip file and rename temporary zip file to the original     
            os.remove(path2zip)
            os.rename(path2zip + '_temp', path2zip)

        logIRD.close()
