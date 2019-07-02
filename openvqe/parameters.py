from dataclasses import dataclass, field
import numpy as np
from enum import Enum

"""
Parameterclasses for OpenVQE modules
All clases are derived from ParametersBase
I/O functions are defined in ParametersBase and are inherited to all derived classes
It is currently not possible to set the default of parameters to None (will confuse I/O routines)
"""


class OutputLevel(Enum):
    SILENT = 0
    STANDARD = 1
    DEBUG = 2
    ALL = 3

@dataclass
class ParametersBase:

    # Parameters which every module of OpenVQE needs

    outfile: str = ""
    # outputlevel is stored as int to not confuse the i/o functions
    _ol: int = field(default=OutputLevel.STANDARD.value)
    def output_level(self) -> OutputLevel:
        """
        Enum handler
        :return: output_level as enum for more convenience
        """
        return OutputLevel(self._ol)

    @staticmethod
    def to_bool(var):
        """
        Convert different types to bool
        currently supported: int, str
        int: 1 -> True, everything else to False
        str: gets converted to all_lowercase then 'true' -> True, everything else to False
        :param var: an instance of the currently supported types
        :return: converted bool
        """
        if type(var) == int:
            return var == 1
        elif type(var) == bool:
            return var
        elif type(var) == str:
            return var.lower() == 'true' or var.lower() == '1'
        else:
            raise Exception("ParameterBase.to_bool(var): not implemented for type(var)==", type(var))

    @classmethod
    def name(cls):
        return cls.__name__

    def print_to_file(self, filename, write_mode='a+'):
        """
        :param filename:
        :param name: the comment of this parameter instance (converted to lowercase)
        if given it is printed before the content
        :param write_mode: specify if existing files shall be overwritten or appended (default)
        """

        string = '\n'
        string += self.name() + " = {\n"
        for key in self.__dict__:
            if isinstance(self.__dict__[key], ParametersBase):
                self.__dict__[key].print_to_file(filename=filename)
                string += str(key) + " : " + str(True) + "\n"
            else:
                string += str(key) + " : " + str(self.__dict__[key]) + "\n"
        string += "}\n"
        with open(filename, write_mode) as file:
            file.write(string)

        return self

    @classmethod
    def read_from_file(cls, filename):
        """
        Reads the parameters from a file
        See the print_to_file function to create files which can be read by this function
        The input syntax is the same as creating a dictionary in python
        where the name of the dictionary is the derived class
        The function creates a new instance and returns this
        :param filename: the name of the file
        :return: A new instance of the read in parameter class
        """

        new_instance = cls()

        keyvals = {}
        with open(filename, 'r') as file:
            found = False
            for line in file:
                if found:
                    if line.split()[0].strip() == "}":
                        break
                    keyval = line.split(":")
                    keyvals[keyval[0].strip()] = keyval[1].strip()
                elif cls.name() in line.split():
                    found = True
        for key in keyvals:
            if not key in new_instance.__dict__:
                raise Exception("Unknown key for class=" + cls.name() + " and  key=", key)
            elif keyvals[key] == 'None':
                new_instance.__dict__[key] = None
            elif isinstance(new_instance.__dict__[key], ParametersBase) and cls.to_bool(keyvals[key]):
                new_instance.__dict__[key] = new_instance.__dict__[key].read_from_file(filename)
            else:

                if key not in cls.__dict__:
                    # try to look up base class
                    assert (key in new_instance.__dict__)
                    if isinstance(new_instance.__dict__[key], type(None)):
                        raise Exception(
                            "Currently unresolved issue: If a ParameterClass has a subclass the parameters can never be set to none"
                        )
                    elif isinstance(new_instance.__dict__[key], bool):
                        new_instance.__dict__[key] = new_instance.to_bool(keyvals[key])
                    else:
                        new_instance.__dict__[key] = type(new_instance.__dict__[key])(keyvals[key])
                elif isinstance(cls.__dict__[key], type(None)):
                    raise Exception(
                        "Default values of classes derived from ParameterBase should NOT be set to None. Use __post_init()__ for that")
                elif isinstance(cls.__dict__[key], bool):
                    new_instance.__dict__[key] = cls.to_bool(keyvals[key])
                else:
                    new_instance.__dict__[key] = type(cls.__dict__[key])(keyvals[key])

        return new_instance


@dataclass
class ParametersHamiltonian(ParametersBase):
    """
    Enter general parameters which hold for all types of Hamiltonians
    """
    transformation: str = "JW"

    # convenience functions
    def jordan_wigner(self):
        if self.transformation.upper() in ["JW", "J-W", "JORDAN-WIGNER"]:
            return True
        else:
            return False

    # convenience functions
    def bravyi_kitaev(self):
        if self.transformation.upper() in ["BK", "B-K", "BRAVYI-KITAEV"]:
            return True
        else:
            return False


@dataclass
class ParametersPsi4(ParametersBase):
    run_scf: bool = True
    run_mp2: bool = False
    run_cisd: bool = False
    run_ccsd: bool = False
    run_fci: bool = False
    verbose: bool = False
    tolerate_error: bool = False
    delete_input: bool = False
    delete_output: bool = False
    memory: int = 8000


@dataclass
class ParametersQC(ParametersHamiltonian):
    """
    Specialization of ParametersHamiltonian
    Parameters for the HamiltonianQC class
    """
    psi4: ParametersPsi4 = ParametersPsi4()
    basis_set: str = ''  # Quantum chemistry basis set
    geometry: str = ''  # geometry of the underlying molecule (units: Angstrom!), this can be a filename leading to an .xyz file or the geometry given as a string
    filename: str = ''
    description: str = ''
    multiplicity: int = 1
    charge: int = 0

    @staticmethod
    def format_element_name(string):
        """
        OpenFermion uses case sensitive hash tables for chemical elements
        I.e. you need to name Lithium: 'Li' and 'li' or 'LI' will not work
        this conenience function does the naming
        :return: first letter converted to upper rest to lower
        """
        assert (len(string) > 0)
        assert (isinstance(string, str))
        fstring = string[0].upper() + string[1:].lower()
        return fstring

    @staticmethod
    def convert_to_list(geometry):
        """
        Convert a molecular structure given as a string into a list suitable for openfermion
        :param geometry: a string specifing a mol. structure. E.g. geometry="h 0.0 0.0 0.0\n h 0.0 0.0 1.0"
        :return: A list with the correct format for openferion E.g return [ ['h',[0.0,0.0,0.0], [..]]
        """
        result = []
        for line in geometry.split('\n'):
            words = line.split()
            if len(words) != 4:  break
            try:
                tmp = (ParametersQC.format_element_name(words[0]),
                       (np.float64(words[1]), np.float64(words[2]), np.float64(words[3])))
                result.append(tmp)
            except ValueError:
                print("get_geometry list unknown line:\n ", line, "\n proceed with caution!")
        return result

    def get_geometry(self):
        """
        Returns the geometry
        If a xyz filename was given the file is read out
        otherwise it is assumed that the geometry was given as string
        which is then reformated as a list usable as input for openfermion
        :return: geometry as list
        e.g. [(h,(0.0,0.0,0.35)),(h,(0.0,0.0,-0.35))]
        Units: Angstrom!
        """
        if self.geometry.split('.')[-1] == 'xyz':
            geomstring, comment = self.read_xyz_from_file(self.geometry)
            self.description = comment
            return self.convert_to_list(geomstring)
        elif self.geometry is not None:
            return self.convert_to_list(self.geometry)
        else:
            raise Exception("Parameters.qc.geometry is None")

    @staticmethod
    def read_xyz_from_file(filename):
        """
        Read XYZ filetype for molecular structures
        https://en.wikipedia.org/wiki/XYZ_file_format
        Units: Angstrom!
        :param filename:
        :return:
        """
        with open(filename, 'r') as file:
            content = file.readlines()
            natoms = int(content[0])
            comment = str(content[1])
            coord = ''
            for i in range(natoms):
                coord += content[2 + i]
            return coord, comment


@dataclass
class ParametersAnsatz(ParametersBase):
    """
    Enter general parameters which hold for all types of Ansatzes
    """

    # have to be assigned
    backend: str = "cirq"


@dataclass
class ParametersUCC(ParametersAnsatz):

    # UCC specific parameters
    # have to be assigned
    decomposition: str = "trotter"
    trotter_steps: int = 1


