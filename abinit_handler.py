import numpy as np

#Atomic Info

allelements={
    "H":[1,1], "He":[2,2], "Li":[3,1], "Be":[4,2], "B":[5,3],  "C":[6,4],  "N":[7,5],  "O":[8,6],  "F":[9,7],  "Ne":[10,8],
    "Na":[11,1], "Mg":[12,2], "Al":[13,3], "Si":[14,4], "P":[15,5],  "S":[16,6],  "Cl":[17,7], "Ar":[18,8], "K":[19,1],  "Ca":[20,2],
    "Sc":[21,3], "Ti":[22,4], "V":[23,5],  "Cr":[24,6], "Mn":[25,7], "Fe":[26,8], "Co":[27,9], "Ni":[28,10], "Cu":[29,11], "Zn":[30,12],
    "Ga":[31,3], "Ge":[32,4], "As":[33,5], "Se":[34,6], "Br":[35,7], "Kr":[36,8], "Rb":[37,1], "Sr":[38,2], "Y":[39,3],  "Zr":[40,4],
    "Nb":[41,5], "Mo":[42,6], "Tc":[43,7], "Ru":[44,8], "Rh":[45,9], "Pd":[46,10], "Ag":[47,11], "Cd":[48,12], "In":[49,3], "Sn":[50,4],
    "Sb":[51,5], "Te":[52,6], "I":[53,7],  "Xe":[54,8], "Cs":[55,1], "Ba":[56,2], "La":[57,11], "Ce":[58,12], "Pr":[59,13], "Nd":[60,14],
    "Pm":[61,15], "Sm":[62,16], "Eu":[63,17], "Gd":[64,18], "Tb":[65,19], "Dy":[66,20], "Ho":[67,21], "Er":[68,22], "Tm":[69,23], "Yb":[70,24],
    "Lu":[71,25], "Hf":[72,12], "Ta":[73,5], "W":[74,6], "Re":[75,7], "Os":[76,8], "Ir":[77,9], "Pt":[78,10], "Au":[79,11], "Hg":[80,12],
    "Tl":[81,3], "Pb":[82,4], "Bi":[83,5], "Po":[84,6], "At":[85,7], "Rn":[86,9], "Fr":[87,1], "Ra":[88,2], "Ac":[89,11], "Th":[90,12],
    "Pa":[91,13], "U":[92,14]
}

# class that reads and stores info from cif to make ABINIT input
class CIFInfo():
    def __init__(
        self,
        cif_file:str
    )->None:
        # initialize attributes
        self.cif_lines:list = []
        self.name:str = ''
        self.atom_ids:list = []
        self.z_vals:list = []
        self.space_group:int = 0
        self.bravais:str = ''
        self.abc = np.zeros(3)
        self.angles = np.zeros(3)
        self.xyz:np.ndarray = np.array([])
        self.mult:list = []
        self.atom_type:list = []
        self.natoms:int = 0
        self.bands:int = 0
        self.kx:int = 0
        self.ky:int = 0
        self.kz:int = 0
        # methods for populating attributes from cif
        self._GetCIFLines(cif_file=cif_file)
        self._FileName()
        self._GetAtomIDs()
        self._GetSpaceGroup()
        for axis in ['a', 'b', 'c']:
            self._GetCellLengths(axis)
        for angle in ['alpha', 'beta', 'gamma']:
            self._GetCellAngles(angle)
        self._GetMultAndXYZ()
        self._CalcNumBands()
        self._SuggestNGKPT()

    #--methods--#

    #----#
    # method for getting all lines of cif file
    def _GetCIFLines(
        self,
        cif_file:str
    )->None:
        # read cif file
        with open(cif_file, 'r') as cif:
            cif_lines = cif.readlines()
        # remove spaces from lines
        cif_lines = [line.strip().split(' ') for line in cif_lines]
        cif_lines = [[foo for foo in line if foo != ''] for line in cif_lines]
        self.cif_lines = cif_lines

    #----#
    # method for constructing ABINIT input file name
    def _FileName(
        self
    )->None:
        # find formula
        for line in self.cif_lines:
            if '_chemical_formula_sum' in line:
                for atom in line[1:]:
                    # do not include ' or number 1
                    atom = ''.join([_ for _ in atom if _ != '1' and _ != "'"])
                    self.name += atom

    #----#
    # method for getting atomic identities
    def _GetAtomIDs(
        self
    )->None:
        # find line with atomic identities
        for line in self.cif_lines:
            if '_chemical_formula_structural' in line:
                for element in line[1:]:
                    element = ''.join([i for i in element if not i.isdigit()])
                    self.atom_ids.append(element)
                break
        # fix first and last atom ids since they have ' attached to the name
        if len(self.atom_ids) != 1:
            self.atom_ids[0] = self.atom_ids[0].split("'")[1]
            self.atom_ids[-1] = self.atom_ids[-1].split("'")[0]
        # get atomic number from atom id
        for element in self.atom_ids:
            z = allelements[element][0]
            self.z_vals.append(z)
        # check for Lanthanides to swap for Yttrium
        self._SwapLaForY()

    #----#
    # method for swapping Lanthanide with Yttrium
    def _SwapLaForY(
        self
    )->None:
        for element in self.atom_ids:
            # check for lanthanide
            if 57 <= allelements[element][0] <= 71:
                swap = input(f'Lanthanide ({element}) found in CIF, swap for Y? (y/n): ')
                # if yes, switch element w/ Yttrium
                if swap == 'y':
                    ind = self.atom_ids.index(element)
                    self.atom_ids[ind] = 'Y'
                    self.z_vals[ind] = allelements['Y'][0]
                # if no, check next atom
                elif swap == 'n':
                    continue
                # if something else, ask again
                else:
                    self._SwapLaForY()

    #----#
    # method for getting space group
    def _GetSpaceGroup(
        self
    )->None:
        # look for space group number and bravais lattice
        for line in self.cif_lines:
            if '_space_group_IT_number' in line:
                self.space_group = int(line[-1])
            if '_space_group_name_H-M_alt' in line:
                self.bravais = line[1].split("'")[1]
            if self.space_group != None and self.bravais != None:
                return

    #----#
    # method for getting cell lengths
    def _GetCellLengths(
        self,
        param:str
    )->None:
        # dict for identifying which axis is being searched for
        abc_identify = {'a':0, 'b':1, 'c':2}
        ind = abc_identify[param]
        # look for a, b, and c
        crys_axis = '_cell_length_' + param
        for line in self.cif_lines:
            if crys_axis in line:
                length = line[-1].split('(')
                length = float(length[0])
                self.abc[ind] = length
                return

    #----#
    # method for getting cell angles
    def _GetCellAngles(
        self,
        param:str
    )->None:
        # dict for identifying which angle is being searched for
        angle_identify = {'alpha':0, 'beta':1, 'gamma':2}
        ind = angle_identify[param]
        # look for alpha, beta, and gamma
        angle = '_cell_angle_' + param
        for line in self.cif_lines:
            if angle in line:
                ang = float(line[-1])
                self.angles[ind] = ang
                return

    #----#
    # method to get line index for multiplicity and xyz
    def _GetLineInd(
        self
    )->int:
        # find loop with multiplicity and xyz data
        for i, line in enumerate(self.cif_lines):
            # once loop is found, find what line number has multiplicity and xyz data
            if '_atom_site_label' in line:
                line_num = i+1
                while True:
                    if len(self.cif_lines[line_num]) == 1:
                        line_num += 1
                    else:
                        return line_num
        return 0
    
    #----#
    # method for calculating number of atoms in primitive cell
    def _CalcNumAtoms(
        self,
    )->None:
        # number atoms in conventional cell
        conv_atoms = np.sum(self.mult)
        # divide conv_atoms depending on Bravais lattice
        if self.bravais == 'P':
            self.natoms = int(conv_atoms)
        elif self.bravais == 'F':
            self.natoms = int(conv_atoms/4)
        else:
            self.natoms = int(conv_atoms/2)

    #----#
    # method for getting multiplicity and reduced x, y, and z
    def _GetMultAndXYZ(
        self
    )->None:
        # get index for which line mulitplicity and xyz starts
        line_num = self._GetLineInd()
        # temporary list for storing coordinates
        xyz = []
        # loop through next n lines until all sites have been parsed
        while True:
            line = self.cif_lines[line_num]
            # check if first entry in line is an atom
            atom_check = line[0]
            atom_check = ''.join([_ for _ in atom_check if _.isalpha()])
            # if not an atom, all sites have been parsed
            if not atom_check in self.atom_ids:
                # format xyz data into numpy array
                self.xyz = np.array(self.xyz)
                # get number of atoms in primitive cell
                self._CalcNumAtoms()
                return
            # get numeric identifier for each atom
            self.atom_type.append(self.atom_ids.index(atom_check) + 1)
            # otherwise get multiplicity and xyz
            self.mult.append(int(line[2]))
            x = float(line[4].split('(')[0])
            y = float(line[5].split('(')[0])
            z = float(line[6].split('(')[0])
            xyz.append(np.array([x,y,z]))
            line_num += 1
            if self.cif_lines[line_num] == []:
                # format xyz data into numpy array
                self.xyz = np.array(self.xyz)
                # get number of atoms in primitive cell
                self._CalcNumAtoms()
                return

    #----#
    # method to calculate number of bands (num electrons/2 + 2*natom)
    def _CalcNumBands(
        self
    )->None:
        # variable for total number of electrons
        num_electrons = 0
        # need num electrons from primitive cell, so divide accordingly
        prim_divisor = np.sum(self.mult)/self.natoms
        # get total number of electrons
        for i, ind in enumerate(self.atom_type):
            atom = self.atom_ids[ind-1]
            num_electrons += self.mult[i]*allelements[atom][1]
        # divide
        num_electrons /= 2*prim_divisor
        bands = num_electrons + 2*self.natoms
        self.bands = round(bands + 0.5)

    #----#
    # method to suggest kpoint sampling along each axis
    def _SuggestNGKPT(
        self
    )->None:
        a = self.abc[0]
        b = self.abc[1]
        c = self.abc[2]
        if 'F' == self.bravais:
            a_prim = np.sqrt(a**2 + b**2)/2
            b_prim = np.sqrt(b**2 + c**2)/2
            c_prim = np.sqrt(c**2 + a**2)/2
        elif 'I' == self.bravais:
            a_prim = b_prim = c_prim = np.sqrt(a**2 + b**2 + c**2)
        elif 'A' == self.bravais:
            a_prim = a
            b_prim = c_prim = np.sqrt(b**2 + c**2)/2
        elif 'C' == self.bravais:
            # if monoclinic
            if self.space_group < 16:
                a_prim = b_prim = np.sqrt(a**2 +  b**2 + 2*a*b*np.cos(self.angles[1]))/2
                c_prim = c
            # otherwise orthorhomic
            else:
                a_prim = b_prim = np.sqrt(a**2 + b**2)/2
                c_prim = c
        # if primitive
        else:
            a_prim = a
            b_prim = b
            c_prim = c
        self.kx = round(a_prim*0.75 + 0.5)
        self.ky = round(b_prim*0.75 + 0.5)
        self.kz = round(c_prim*0.75 + 0.5)

# function for writing ABINIT input file
def WriteInput(
    cif:CIFInfo,
    paw:bool=False,
    potential_path:str='/share/apps/dfprograms/abinit_pots/'
)->None:
    file_name = cif.name + '_ecut.in'

    files_file = open(cif.name + '_ecut.files', 'w')
    print(
f'''{cif.name+'_ecut.in'}
{cif.name+'_ecut.out'}
{cif.name+'_ecut_i'}
{cif.name+'_ecut_o'}

''',
file = files_file,
end=''
)
    if paw:
        for atom in cif.atom_ids:
            pot = atom + '.GGA_PBE-JTH.xml'
            print(potential_path + 'paw_pbe/ATOMICDATA/' + pot, file=files_file)
    else:
        for atom in cif.atom_ids:
            pot = f'{allelements[atom][0]}' + atom.lower() + f'.{allelements[atom][1]}.hgh'
            print(potential_path + '/lda_hgh/' + pot, file=files_file)

    files_file.close()

    input_file = open(file_name, 'w')
    print(
f'''! File made by cif2abinit

! Default options
    nstep    100    ! number of SCF steps
    occopt   7      ! gaussian smearing
    tsmear   0.005  ! good default for metals, user may want to check this
    tolvrs   1.0E-8 ! convergence criterion, difference of potential between steps
     prtwf   0      ! 1 to print WFK file, 0 does not print WFK
!   istwfk   (NKPT)*1 ! write WFK by k-point number
''',
file=input_file,
end=''
)

    if paw:
        print(
f'''
! PAW potential files
   pp_dirpath  "{potential_path + 'paw_pbe/ATOMICDATA'}"     ! path to PAW potentials, change to sp if needed
   pseudos   "{', '.join([_+'.GGA_PBE-JTH.xml' for _ in cif.atom_ids])}"   ! PAW potentials
''',
file=input_file,
end=''
)
    else:
        print(
f'''
! LDA pseudopotential files
   pp_dirpath  "{potential_path + 'lda_hgh'}"     ! path to LDA HGH potentials
   pseudos   "{', '.join([f'{allelements[_][0]}'+_.lower()+f'.{allelements[_][1]}.hgh' for _ in cif.atom_ids])}"   ! LDA HGH potentials
''',
file=input_file,
end=''
)

    print(
f'''
! Atomic info
    ntypat   {len(cif.atom_ids)}   ! number of elements
     znucl   {' '.join([str(_) for _ in cif.z_vals])}   ! atomic numbers
     natom   {cif.natoms}   ! number atoms in primitive cell
     nband   {2*cif.bands}   ! number of bands (electrons/2 + 2*natom)

! Cell info
     acell   {' '.join([str(_) for _ in cif.abc])} angstrom  ! conventional cell lengths
    angdeg   {' '.join([str(_) for _ in cif.angles])}  ! conventional cell angles
    brvltt  -1    ! convert to primitive cell, 0 to leave as conventional cell
!  chkprim   0    ! uncomment to run calculation on nonprimitive cell
    tolsym   1.0E-8  ! recommended (not default) tolerance on symmetry
   spgroup   {cif.space_group}   ! space group number
   spgaxor   1   ! axis orientation
   spgorig   1   ! choice of origin, may not always be 1
     natrd   {len(cif.mult)}  ! number of sites
     typat   {' '.join([str(_) for _ in cif.atom_type])}   ! atom types for each position
      xred             ! fractional atomic positions
''',
file=input_file,
end=''
)

    for xyz in cif.xyz:
        round_xyz = np.round(xyz, 3)
        # add more precision to decimals
        for i, val in enumerate(round_xyz):
            if val == 0.333:
                xyz[i] = 0.333333333333
            if val == 0.667:
                xyz[i] = 0.666666666667
        frac_pos = ' '.join([str(_) for _ in xyz])
        print(f'              {frac_pos}', file=input_file)

    print(
f'''
! Energy cutoff convergence test
    ndtset     4      ! number of datasets to run
     ecut1     20     ! first dataset energy cutoff
     ecut2     25     ! second
     ecut3     30     ! third
     ecut4     35     ! fourth
     ngkpt     1 1 1  ! only compute gamma point during ecut test
''',
file=input_file,
end=''
)
    if paw:
        print(
f'''
! PAW options
!   ndtset     4      ! number of datasets
  pawecutdg1   20     ! first energy cutoff of PAW double grid
  pawecutdg2   25     ! second
  pawecutdg3   30     ! third
  pawecutdg4   35     ! fourth
! pawspnorb    1      ! turns on spin-orbit coupling with PAW
''',
file=input_file,
end=''
)

    print(
f'''
! k point grid convergence test
!   ndtset     4      ! number of datasets to run
!   ngkpt1     {cif.kx} {cif.ky} {cif.kz}    ! first dataset k point grid dimensions
!   ngkpt2     {cif.kx + 2} {cif.ky + 2} {cif.kz + 2}    ! second
!   ngkpt3     {cif.kx + 4} {cif.ky + 4} {cif.kz + 4}    ! third
!   ngkpt4     {cif.kx + 6} {cif.ky + 6} {cif.kz + 6}    ! fourth
    shiftk     0.0 0.0 0.0     ! gamma centered grid

! Geometry optimization
!   ionmov     3     ! optimization algorithm, try 2 if 3 fails
!    ntime     50    ! max number of move steps
!   prtcif     1     ! set to 1 to print geometry to CIF file, 0 to not print
!  optcell     0     ! 0 for ionic positions, 2 for ionic and lattice optimization
!  dilatmx     1.15  ! max amount cell is allowed change
!   ecutsm     13.6 eV ! smearing applied to ecut to accomodate cell changes

! Spin polarization
!   nsppol     2     ! turns on spin polarization, 1 for antiferromagnetism
!   nspden     2     ! 2 for scalar magnetization, 4 for vector (requires nsppol 1 and nspinor 2)
!   spinat     MANUAL ! Initial magnetization
                      ! for each site, specify x, y, and z magnetization
                      ! units of hbar/2

! Spin orbit coupling
!   nspinor    2     ! turns on spin orbit coupling
                     ! automatically set if pawspnorb is 1

! Density of states
!    prtdos    3     ! atom projected DOS, 2 for just total DOS
!    ratsph    MANUAL ! only needed for prtdos 3
                      ! radius of each atom type, this can come from Bader or Hirshfeld analysis
                      ! if using PAW, this will be automatically set to radius of PAW sphere

! Chemical Pressure
!    ndtset    3     ! number of datasets
! scalecart1   3*1.005 ! slightly expand lattice
! scalecart2   3*1.000 ! equilibrium lattice
! scalecart3   3*0.995 ! slightly contract lattice
!   usekden    1     ! get kinetic energy density
!   prtkden    1     ! print kinetic energy density
!    prtpot    1     ! print Kohn-Sham potential
!    prtvha    1     ! print Hartree potential
!    prtvxc    1     ! print exchange-correlation potential
!   prtvhxc    1     ! print sum of VHA and VXC
!     ngfft    {cif.kx*20} {cif.ky*20} {cif.kz*20}  ! FFT grid dimensions
                         ! dimensions must be divisible by corresponding kpt dimension
''',
file=input_file,
end=''
)

    input_file.close()

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('cif', type=str, help='Name of CIF File')
    arg=parser.parse_args()
    cif = CIFInfo(arg.cif)
    WriteInput(cif)