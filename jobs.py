from ssh_handler import SSH
from rdrive_interface import RDrive
import time

class Jobs():
    def __init__(
        self,
        name:str = '',
        step:int = 0,
        rdrive_path:str = '',
        cluster_path:str = '',
        ssh_conn:SSH = SSH(),
        rdrive_conn:RDrive = RDrive(),
        cv_mode:int = 11
    ):
        self.name = name
        self.step = step
        self.rdrive_path = rdrive_path
        self.cluster_path = cluster_path
        self.ssh = ssh_conn
        self.rdrive = rdrive_conn
        self.cv_mode = cv_mode

        # queue scripts for clusters
        self.qscripts = {
            'spark-login':
            [
                '/software/groups/fredrickson_group', 
                '/qabinit7 -p pre -n 1 -c 64', 
                '/qnonlocal', 
                '/qCPpackage4', 
                '/qCPpackage', 
                '/bin2xsf', 
                '/qbandU_atomden'
            ],
            'kestrel':
            [
                '/share/apps/dfprograms', 
                '/qabinit-8.10 -np 32', 
                '/qnonlocal', 
                '/qCPpackage4', 
                '/qCPpackage', 
                '/bin2xsf', 
                '/qbandU_atomden'
            ]
        }
        base_queue = self.qscripts[self.ssh.hostname][0]
        self.abinit_queue = base_queue + self.qscripts[self.ssh.hostname][1]
        self.nonlocal_queue = base_queue + self.qscripts[self.ssh.hostname][2]
        self.CPbraMO_queue = base_queue + self.qscripts[self.ssh.hostname][3]
        self.CPstd_queue = base_queue + self.qscripts[self.ssh.hostname][4]
        self.bin2xsf = base_queue + self.qscripts[self.ssh.hostname][5]
        self.raMO_queue = base_queue + self.qscripts[self.ssh.hostname][6]

        # directories for various steps of chemical pressure calculation
        self.queue_dir = {
            0:'/ecut',
            1:'/kptmesh',
            2:'/opt1',
            3:'/opt2',
            4:'/static'
        }
    #-------------METHODS-------------#

    # method for checking total energy convergence
    # 5 meV/atom convergence default
    def _ConvergeneceChecker(
        self,
        check:str,
        convergence = 0.005
    )->int:
        # get total energy values
        etotal = self.ssh.cmd_string(
            commands = [
                f'cd {self.cluster_path + "/" + check}',
                f'grep etotal *log'
            ]
        )

        # parse etotal values
        etotal = etotal.strip().split(' ')
        etotal = [ch for ch in etotal if ch != '']
        etotal = [float(ch) for i, ch in enumerate(etotal) if i % 2]
        
        # get number of atoms from input
        natom = self.ssh.cmd_string(
            commands = [
                f'cd {self.cluster_path + "/" + check}',
                'grep natom *log'
            ]
        )
        natom = natom.strip().split(' ')
        natom = [ch for ch in natom if ch != '']
        natom = int(natom[-1])

        # convert from Ha/cell to eV/atom
        Ha2eV = 27.2114/natom
        etotal = [Ha2eV*eng for eng in etotal]

        # check for convergence
        for i in range(len(etotal)-1):
            eng1 = etotal[i]
            eng2 = etotal[i+1]
            if eng1 - eng2 <= convergence:
                return i + 1

        # negative if convergence is not reached
        return -1
    
    # update input when moving from ecut to kptmesh
    def _EcutToKptmesh(
        self
    ):
        # check ecut convergence
        convergence = self._ConvergeneceChecker(check = 'ecut')
        if convergence < 0:
            print('Energy cutoff not converged, edit input to test higher values')
            raise SystemExit()
        
        # edit input
        # read in whole input file
        input_path = self.cluster_path + '/ecut/*.in'
        input_file = self.ssh.cat(path = input_path)
        input_file = input_file.split('\n')

        # replace lines
        for i, line in enumerate(input_file):
            if 'ecut' in line and f'ecut{convergence}' not in line:
                input_file[i] = '! ' + line
            if f'ecut{convergence}' in line:
                input_file[i] = line.replace(f'ecut{convergence}', 'ecut')
            if '! Energy cutoff convergence' in line:
                input_file[i+1] = '! ndtset 4'
            if 'ngkpt ' in line:
                input_file[i] = '! ' + line
            if '! k point grid convergence' in line:
                input_file[i+1] = 'ndtset 4'
            if 'ngkpt' in line and 'ngkpt ' not in line:
                input_file[i] = line[1:]
        
        # write file to kptmesh directory
        lines = '\n'.join(input_file)
        self.ssh.cmd_string(
                commands = [
                    f'cd {self.cluster_path + "/kptmesh"}',
                    f'printf "{lines}" >> {self.name + ".in"}'
                ]
            )
        
        # copy files file to kptmesh directory
        kptmesh_files = '/kptmesh/' + self.name + '.files'
        self.ssh.cmd_string(
            commands = [
                f'cp {self.cluster_path + "/ecut/*.files"} {self.cluster_path + kptmesh_files}'
            ]
        )

        # start kptmesh job
        q_name = self.name + '_kptmesh'
        self.ssh.cmd_string(
            commands = [
                f'{self.abinit_queue} {q_name}'
            ]
        )

    # update input when moving from kptmesh to opt1
    def _KptmeshToOpt1(
        self
    ):
        pass

    # update input when moving from opt1 to opt2
    def _Opt1ToOpt2(
        self
    ):
        pass

    # update input when moving from opt2 to static
    def _Opt2ToStatic(
        self
    ):
        pass

    # method for updating directory with new inputs
    def _UpdateDir(
        self,
        update_dir:str
    ):
        prev_step = self.step - 1
        if prev_step < 0:
            return
        
    # check if ABINIT job completed without error
    @property
    def error(
        self
    )->bool:
        # at step 7, then continue
        if self.step > 6:
            return False
        
        # figure out which chemical pressure directory exists
        if self.cv_mode == 11:
            cp_dir = '/cpdir_std'
        else:
            cp_dir = '/cpdir'

        # dictionary of grep arguments to check if calculation completed without error
        check_args = {
            0:['/ecut', 'Calculation complete', '*.out'],
            1:['/kptmesh', 'Calculation complete', '*.out'],
            2:['/opt1', 'Calculation complete', '*.out'],
            3:['/opt2', 'Calculation complete', '*.out'],
            4:['/static', 'Calculation complete', '*.out'],
            5:['/nonlocal', 'Done', '*.nonlocal'],
            6:[cp_dir, 'calculation complete', '*cplog'],
        }

        job_path = self.cluster_path + check_args[self.step][0]
        grep_arg1 = check_args[self.step][1]
        grep_arg2 = check_args[self.step][2]

        check = self.ssh.cmd_string(
            commands = [
                f'cd {job_path}',
                f'grep "{grep_arg1}" {grep_arg2}'
            ]
        )

        # nonlocal step has two outputs, check both
        if check_args[self.step][0] == '/nonlocal':
            if len(check.split('Done')) == 3:
                return False
            return True

        # other steps have one out, make sure grep returns something
        if check != '':
            return False
        return True
        
    # general queue method for abinit jobs
    def _QueueAbinit(
        self
    ):
        # dictionary that matches step number to queue directory
        queue_dir = self.queue_dir[self.step]

        # check if directory exists
        run_dir = self.cluster_path + queue_dir
        if self.ssh.check_dir(run_dir):
            self.ssh.mkdir(run_dir)

        # update directory with new inputs
        self._UpdateDir(run_dir)
        
        # queue job based off of step number
        self.ssh.cmd_string(
            commands = [
                f'cd {run_dir}',
                f'{self.abinit_queue} {self.name}'
            ]
        )

    # method for nonlocal step
    def _QueueNonlocal(
        self
    ):
        # check if directory exists
        nonlocal_dir = self.cluster_path + '/nonlocal'
        if self.ssh.check_dir(nonlocal_dir):
            self.ssh.mkdir(nonlocal_dir)

        # link files from static job to nonlocal directory
        self.ssh.cmd_string(
            commands = [
                f'cd {nonlocal_dir}',
                'ln -s ../static/*WFK .',
                'ln -s ../static/*.out .',
                'ln -s ../static/*_DEN .'
            ]
        )

        # queue nonlocal for dataset 1 and dataset 3
        name = self.name + "_static"
        self.ssh.cmd_string(
            commands = [
                f'cd {nonlocal_dir}',
                f'{self.nonlocal_queue} {name + ".out"} {name} 1'
            ]
        )

        self.ssh.cmd_string(
            commands = [
                f'cd {nonlocal_dir}',
                f'{self.nonlocal_queue} {name + ".out"} {name} 3'
            ]
        )
    
    # method for creating raMO atom cells
    def _raMOStep(
        self,
        dftcp_dir:str,
        energy_sampling:float,
        p_cell_tol:float
    ):
        # queue raMO step
        self.ssh.cmd_string(
            commands = [
                f'cd {dftcp_dir}',
                f'{self.raMO_queue} {self.name}_static.out {self.name}_static_o_DS2 1 0 {energy_sampling} {p_cell_tol}'
            ]
        )

        while True:
            # only return once raMO has finished
            status = self.ssh.cmd_string(
                commands = [
                    'squeue | grep $USER'
                ]
            ).split('\n')
            status = [[ch for ch in job.strip().split(' ') if ch != ''] for job in status]

            # stat[4] is one of PENDING, RUNNING, or COMPLETE, stat[2] is name of job
            for stat in status:
                if stat == []:
                    return
                elif stat[2].startswith(f'{self.name}') and stat[4] == 'COMPLETE':
                    return
            
            # wait a minute before checking again
            time.sleep(30)
    
    # method for queuing chemical pressure job
    def _QueueChemicalPressure(
        self,
        energy_sampling:float = 0.5,
        p_cell_tol:float = 0.5
    ):
        # get directory path and method 
        if self.cv_mode == 12:
            dftcp_dir = self.cluster_path + '/cpdir'
            method = self.CPbraMO_queue
        else:
            dftcp_dir = self.cluster_path + '/cpdir_std'
            method = self.CPstd_queue       

        # function for queuing chemical pressure job
        def qcp():
            self.ssh.cmd_string(
                commands = [
                    f'cd {dftcp_dir}',
                    f'{method} {self.name}_static.out {self.name}_static'
                ]
            )
            
        # check if directory exists
        if self.ssh.check_dir(dftcp_dir):
            self.ssh.mkdir(dftcp_dir)

        # link files from static and nonlocal directories to chemical pressure directory
        self.ssh.cmd_string(
            commands = [
                f'cd {dftcp_dir}',
                'ln -s ../static/* .',
                'ln -s ../nonlocal/*.xsf .'
            ]
        )

        # make xsf file for equilibrium volume denisty
        self.ssh.cmd_string(
            commands = [
                f'cd {dftcp_dir}',
                f'{self.bin2xsf} *DS2_DEN'
            ]
        )

        # if using new method (cv_mode = 12), start raMO step
        if self.cv_mode == 12:
            self._raMOStep(
                dftcp_dir = dftcp_dir,
                energy_sampling = energy_sampling,
                p_cell_tol = p_cell_tol
            )

        # queue chemical pressure job
        # first procedure is for standard method, requires three runs
        # first run generate .ini file
        qcp()
        
        # edit .ini file
        ini_file = self.ssh.cat(path = dftcp_dir + '/*.ini')
        ini_file = ini_file.split('\n')
        for i, line in enumerate(ini_file):
            if 'CV_MODE' in line:
                ini_file[i] = f'CV_MODE {self.cv_mode}'
                break
        print(ini_file)
        ini_file = '\n'.join(ini_file)
        print(ini_file)
        self.ssh.cmd_string(
            commands = [
                f'cd {dftcp_dir}',
                'rm *.ini',
                f'printf "{ini_file}" >> {self.name + "_static.ini"}'
            ]
        )
    
        # if using Au, Cu, or Ag then switch semicore on
        if 'Au' in self.name or 'Ag' in self.name or 'Cu' in self.name:
            for i, line in enumerate(ini_file):
                if 'Au' in line or 'Cu' in line or 'Ag' in line:
                    ini_file[i+1] = '1'

        # second run, for cv_mode 12 this queues job
        # for cv_mode 11 this sets up occ files
        qcp()

        # third run only for cv_mode 11 to queue job
        if self.cv_mode == 11:
            # wait some time to make sure occ files are fully made
            time.sleep(5)
            qcp()        
 