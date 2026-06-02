# AutoDFTCP
Workflow for automatically queuing and managing density functional theory - chemical pressure calculations.
Designed exclusively for internal Fredrickson Group use.

------------------------------------------------------------------------------------------------------- 
<h1><p align="center">OVERVIEW</p></h1>

<p align="justify">A package that interfaces with HPC clusters to automate scheduling of DFT-Chemical Pressure jobs.</p>

<p align="justify">This package is designed to be used by Fredrickson Group members only as many of the cluster scripts called by this package have permissions restricted to the members of the group. Furthermore, access to clusters is restricted to UW-Madison affiliates. The modules here are available to be adapted to any other cluster/research group, but maintainers of this package have no expectation to provide support or assistance of any kind for these purposes.</p>

-------------------------------------------------------------------------------------------------------  
<h1><p align="center">INSTALLATION INSTRUCTIONS</p></h1>

<h2><p align="center">THROUGH GITHUB</p></h2>

1) Inside that directory type on the command line  
   "git clone https://github.com/pcross0405/AutoDFTCP.git"

2) Type "cd AutoDFTCP"

3) Make sure you have python's build tool up to date with  
   "python3 -m pip install --upgrade build"

4) Once up to date type  
   "python3 -m build"

5) This should create a "dist" directory with a .whl file inside

6) On the command line type  
   "pip install dist/*.whl" 
   
-------------------------------------------------------------------------------------------------------  
<h1><p align="center">DEPENDENCIES</p></h1>

REQUIRED FOR ESTABLISHING SSH CONNECTION TO CLUSTER

   - [paramiko](https://www.paramiko.org/)

   - [fabric](https://www.fabfile.org/)

   - [pywin32](https://pypi.org/project/pywin32/)

---------------------------------------------------------------------------------------------------------  
<h1><p align="center">REPORTING ISSUES</p></h1>

Please report any issues [here](https://github.com/pcross0405/AutoDFTCP/issues)  

-------------------------------------------------------------------------------------------------------------------------  
<h1><p align="center">TUTORIAL</p></h1>

An example script for setting up a queue from Research Drive is given below.
-------------------------------------------------------------------------------------------
<pre>
from abi_queue import QueueManager
import time

# cv_mode = 11 for standard DFT-CP method as published in: 
# Self-Consistent Chemical Pressure Analysis: Resolving Atomic Packing Effects through the Iterative Partitioning of Space and Energy
# Kyana M. Sanders, Jonathan S. Van Buskirk, Katerina P. Hilleke, and Daniel C. Fredrickson
# Journal of Chemical Theory and Computation 2023 19 (13), 4273-4285
# DOI: 10.1021/acs.jctc.3c00368
#
# cv_mode = 12 for new DFT-CP method awaiting publication as of 2 June 2026
#
# use paramiko connection as fabric connection is still underdevelopment

test = QueueManager(
    rdrive_path = r'\\research.drive.wisc.edu\dcfredrickso\AutoCP',
    rdrive_user = '[your username here]',
    hpc_address = '[cluster address here]',
    hpc_user = '[your username here]',
    cv_mode = 11,
    paramiko = True
)

# wait 10 seconds for QueueManager to read files from research drive
time.sleep(10)

# set up queue
test._QueueHandler()

# wait 10 seconds to make sure QueueHandler has time to post all jobs in queue to cluster
time.sleep(10)

# get number of queued jobs
num_jobs = len(test.running_jobs)

# run until all jobs complete
while len(test.completed_jobs) < num_jobs:
    test._CompleteHandler()
    print(test._JobStats)
    time.sleep(20)
<pre>
