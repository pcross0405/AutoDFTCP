from ssh_handler import SSH
from rdrive_interface import RDrive
from jobs import Jobs

class QueueManager():
    def __init__(
        self, 
        rdrive_user:str = '', 
        rdrive_password:str = '',
        rdrive_path:str = '',
        hpc_user:str = '',
        hpc_address:str = '',
        cv_mode:int = 11
    ):
        self.rdrive_user = rdrive_user
        self._rdrive_password = rdrive_password
        self.rdrive_path = rdrive_path
        self.hpc_user = hpc_user
        self.hpc_address = hpc_address

        # dicts for sourcing actions based on host address
        # for calling qscripts
        self.qscripts = {
            'spark-login.chtc.wisc.edu':'/software/groups/fredrickson_group/qabinit7 -p pre -n 1 -c 64',
            'kestrel.chem.wisc.edu':'/share/apps/dfprograms/qabinit-8.10 -np 32'
        }

        # for making a new directory
        self.new_dirs = {
            'spark-login.chtc.wisc.edu':f'/scratch/{self.hpc_user}/autocp',
            'kestrel.chem.wisc.edu':f'/home/{self.hpc_user}/autocp'
        }

        # establish connection to research drive
        self.rdrive = RDrive(
            username = rdrive_user,
            password = rdrive_password,
            server_path = rdrive_path
        )

        # establish connection to cluster
        self.ssh = SSH(
            user = hpc_user,
            host = hpc_address
        )

        # make sure autocp directory exists on cluster
        if self.ssh.check_dir(self.new_dirs[hpc_address]):
            self.ssh.mkdir(self.new_dirs[hpc_address])

        # fetch queue from research drive
        self.queued_jobs = self.rdrive.AutoCPFetch()
        self.running_jobs = []
        self.completed_jobs = []
        self.error_jobs = []

        # create job objects to track progress of calculations
        self.jobs:dict[str,Jobs] = {}
        for job in self.queued_jobs:
            name = job.split('\\')[-1]
            self.jobs[name] = self.ConstructJob(job_path = job, cv_mode = cv_mode)

    #---------METHODS---------#
    # get queued jobs
    @property
    def queued(
        self
    )->list:
        return [compound.split('\\')[-1] for compound in self.queued_jobs]
    
    # get running jobs
    @property
    def running(
        self
    )->list:
        return [compound.split('\\')[-1] for compound in self.running_jobs]
    
    # get completed jobs
    @property
    def completed(
        self
    )->list:
       return [compound.split('\\')[-1] for compound in self.completed_jobs] 

    # get current queue
    @property
    def queue_status(
        self
    ):
        return self.ssh.cmd_string(
            commands = [
                'squeue | grep $USER'
            ]
        )
    
    # get job status
    @property
    def _JobStats(
        self
    )->dict[str, list]:
        job_stats = {
            'PENDING':[],
            'RUNNING':[],
            'COMPLETE':[],
            'ERROR':[]
        }

        status = self.queue_status.split('\n')
        status = [[ch for ch in job.strip().split(' ') if ch != ''] for job in status]

        # stat[4] is one of PENDING, RUNNING, or COMPLETE, stat[2] is name of job
        for stat in status:
            if stat == []:
                continue
            elif stat[4] == 'PD':
                stat[4] = 'PENDING'
            elif stat[4] == 'R':
                stat[4] = 'RUNNING'
            elif stat[4] == 'C':
                stat[4] = 'COMPLETE'
            job_stats[stat[4]].append(stat[2])

        # COMPLETE status does not stick around for long before it is taken off of the job status list
        # Check is job is in self.running, but now is not and add to COMPLETE if not there
        total_jobs = [j.split('_')[0] for each_status in job_stats.values() for j in each_status]
        for job in self.running:
            if job not in total_jobs and job not in self.error_jobs:
                if self.jobs[job].error:
                    self.error_jobs.append(job)
                else:
                    job_stats['COMPLETE'].append(job)

        job_stats['ERROR'] = self.error_jobs
        return job_stats
    
    # job class construction
    def ConstructJob(
        self,
        job_path:str,
        cv_mode:int
    )->Jobs:
        name = job_path.split('\\')[-1]
        # check if starting from scratch or from existing input
        if name.endswith('.cif'):
            step = 0
        else:
            step = 4

        job = Jobs(
            name = name,
            rdrive_path = job_path,
            cluster_path = self.new_dirs[self.hpc_address] + f'/{name}',
            step = step,
            ssh_conn = self.ssh,
            rdrive_conn = self.rdrive,
            cv_mode = cv_mode
        )
        return job

    # update queue
    def UpdateQueue(
        self
    ):
        for p in self.rdrive.AutoCPFetch():
            self.queued_jobs.append(p)
            name = p.split('\\')[-1]
            self.jobs[name] = self.ConstructJob(p) #type: ignore
    
    # checker for directory
    def _CheckDir(
        self,
        name:str,
    )->str:
        check_dir = self.new_dirs[self.hpc_address] + f'/{name}'
        if self.ssh.check_dir(check_dir):
            self.ssh.mkdir(check_dir)

        return check_dir

    # queue jobs to cluster from pre-existing input file
    def _QueueInput(
        self,
        file_name:str
    ):
        in_file = file_name + '.in'
        files_file = file_name + '.files'

        # make sure directory exists to copy to
        name = file_name.strip().split('\\')[-1]
        q_dir = self._CheckDir(name = name + '/static')

        # copy in_file to cluster
        with open(in_file, 'r') as f:
            lines = f.read()
            self.ssh.cmd_string(
                commands = [
                    f'cd {q_dir}',
                    f'printf "{lines}" >> {name + "_static" + ".in"}'
                ]
            )
        
        # copy files_file to cluster
        with open(files_file, 'r') as f:
            lines = f.read()
            self.ssh.cmd_string(
                commands = [
                    f'cd {q_dir}',
                    f'printf "{lines}" >> {name + "_static" + ".files"}'
                ]
            )

        # queue job
        q_name = name + '_static'
        self.ssh.cmd_string(
            commands = [
                f'cd {q_dir}',
                f'{self.qscripts[self.hpc_address]} {q_name}'
            ]
        )

    # function for transitioning queue to running
    def _QueueHandler(
        self
    ):
        while self.queued_jobs:
            file_on_deck = self.queued_jobs.pop()
            name = file_on_deck.split('\\')[-1]

            # make new directories for jobs
            self._CheckDir(name = name)

            # update running jobs
            self.running_jobs.append(file_on_deck)

            if file_on_deck.endswith('.cif'):
                # break out function to make inputs from scratch
                pass

            else:
                # break out function to handle existing input
                self._QueueInput(file_name = file_on_deck)
        
    # copy files via smbclient
    def smbCopy(
        self,
        local_path:str,
        remote_path:str
    ):
        # make directory if it doesnt exist
        if not self.rdrive.CheckDir(remote_path):
            self.rdrive.mkdir(remote_path)

        # copy file from local path to remote path
        self.ssh.smb(
            remote_path = remote_path,
            local_path = local_path,
            password = self._rdrive_password
        )

    # function for transitioning running to complete
    def _CompleteHandler(
        self
    ):
        # get status on all jobs
        status = self._JobStats

        # check if all jobs have completed or errored
        if not status['PENDING'] and not status['RUNNING'] and not status['COMPLETE']:
            if status['ERROR']:
                raise SystemExit(f'All jobs have completed with some errors in jobs: {status["ERROR"]}.')
            else:
                raise SystemExit('All jobs have completed with no errors.')
        
        # updated completed job steps
        while status['COMPLETE']:
            compound = status['COMPLETE'].pop()
            step = self.jobs[compound].step
            if step == 0:
                self.jobs[compound]._EcutToKptmesh()
            elif step == 1:
                self.jobs[compound]._KptmeshToOpt1()
            elif step == 2:
                self.jobs[compound]._Opt1ToOpt2()
            elif step == 3:
                self.jobs[compound]._Opt2ToStatic()
            elif step == 4:
                self.jobs[compound]._QueueNonlocal()
            elif step == 5:
                self.jobs[compound]._QueueChemicalPressure()
            # once chemical pressure has finished, copy files to research drive
            elif step == 6:
                remote = f'AutoCP/{self.hpc_user}/completed'
                local = self.new_dirs[self.hpc_address]
                files_to_save = [
                    '*coeff',
                    '*geo',
                    '*cell',
                    '*cplog',
                    '*DS2_DEN.xsf'
                ]
                if compound not in self.completed:
                    self.completed_jobs.append(compound)
                    compound_local = local + f'/{compound}'
                    compound_remote = remote + f'/{compound}'

                    # save files to research drive
                    # smbclient only available on spark
                    if self.hpc_address.startswith('spark'):

                        # check if save directory on research drive exists
                        if not self.rdrive.CheckDir(compound_remote):
                            self.rdrive.mkdir(compound_remote)

                        for file in files_to_save:
                            self.ssh.smb(
                                remote_path = compound_remote,
                                local_path = compound_local + f'/{file}',
                                password = self._rdrive_password
                            )
            # increment job step after staging next step
            self.jobs[compound].step += 1
