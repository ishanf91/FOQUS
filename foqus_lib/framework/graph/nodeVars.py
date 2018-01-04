"""
NodeVars.py

* This contains the classes for node variables
* Class for lists of node variables

John Eslick, Carnegie Mellon University, 2014

This Material was produced under the DOE Carbon Capture Simulation
Initiative (CCSI), and copyright is held by the software owners:
RISE, LANS, LLNS, LBL, PNNL, CMU, WVU, et al. The software owners
and/or the U.S. Government retain ownership of all rights in the
CCSI software and the copyright and patents subsisting therein. Any
distribution or dissemination is governed under the terms and
conditions of the CCSI Test and Evaluation License, CCSI Master
Non-Disclosure Agreement, and the CCSI Intellectual Property
Management Plan. No rights are granted except as expressly recited
in one of the aforementioned agreements.
"""

from collections import OrderedDict
import json
import math
import logging
import copy
from foqus_lib.framework.foqusException.foqusException import *
from foqus_lib.framework.uq.Distribution import Distribution

ivarScales = [ # list of scaling options for input variables
    'None',
    'Linear',
    'Log',
    'Power',
    'Log 2',
    'Power 2']

class NodeVarEx(foqusException):
    def setCodeStrings(self):
        self.codeString[0] = 'Other exception'
        self.codeString[3] = 'Not a valid variable attribute'
        self.codeString[8] = 'Error unscaling'
        self.codeString[9] = 'Error scaling'
        self.codeString[11] = 'Invalid data type'
        self.codeString[22] = 'Time step index out of range'

class NodeVarListEx(foqusException):
    def setCodeStrings(self):
        self.codeString[0] = 'Other exception'
        self.codeString[2] = 'Node does not exist'
        self.codeString[3] = 'Variable does not exist'
        self.codeString[5] = 'Node name already in use, cannont add'
        self.codeString[6] = ('graph is reserved and cannot be used'
                              ' as a node name')
        self.codeString[7] = 'Var name already in use, cannont add'

class NodeVarList(OrderedDict):
    """
    This class contains a dictionary of dictionaries the first key is the node
    name, the second key is the variable name.
    """
    def __init__(self):
        """
        Initialize the variable list dictionary
        """
        OrderedDict.__init__(self)

    def clone(self):
        """
        Make a new copy of a variable list
        """
        newOne = NodeVarList()
        sd = self.saveDict()
        newOne.loadDict(sd)
        return newOne

    def addNode(self, nodeName):
        """
        Add a node to the variable list

        Args:
            nodeName = a string name for the node to add, must not exist already
        """
        if nodeName in self:
            raise NodeVarListEx(code=5, msg=str(nodeName))
        self[nodeName] = OrderedDict()

    def addVariable(self, nodeName, varName, var=None):
        """
        Add a variable name to a node:

        Args:
            nodeName: to node to add a variable to
            varName: the variable name to add
            var: a NodeVar object or None to create a new variable
        """
        if nodeName not in self:
            raise NodeVarListEx(2, msg=nodeName)
        if varName in self[nodeName]:
            raise NodeVarListEx(7, msg=varName)
        if not var:
            var = NodeVars()
        self[nodeName][varName] = var
        return var

    def get(self, name, varName=None):
        '''
        This returns a variable looked up by a name string where the node name
        is separated from the variable name by a period or if two arguments are
        given they are the node name and variable name.  For one argument, the
        first period in the name is assumed to be the separator.  This means
        the node names should not contain periods, but it okay for the variable
        name to contain a period.
        '''
        if varName == None:
            n = name.split('.', 1) #n[0] = node name, n[1] = var name
            name = n[0]
            varName = n[1]
        try:
            return self[name][varName]
        except KeyError as e:
            if n[0] in self:
                raise NodeVarListEx(3, msg=n[1])
            else:
                raise NodeVarListEx(2, msg=n[0])


    def createOldStyleDict(self):
        """
        This can be used to create the f and x dictionaries for a graph. I'm
        trying to phase this out, but I'm using in for now so I can make
        smaller changes working to new variable list objects
        """
        self.odict = OrderedDict()
        for node in sorted(self.keys(), key=lambda s: s.lower()):
            for var in sorted(self[node].keys(), key=lambda s: s.lower()):
                self.odict['.'.join([node, var])] = self[node][var]
        return self.odict
    

    def compoundNames(self, sort=True):
        """
        Create a list of compound names for variables

        Args:
            sort: if true sort the names alphabetically
        """
        l = []
        for node in self.keys():
            for var in self[node].keys():
                l.append('.'.join([node, var]))
        if sort:
            return sorted(l, key = lambda s: s.lower())
        else:
            return l

    def splitName(self, name):
        """
        Split the name at the first '.'' to get a node and variable name
        """
        return name.split('.',1)

    def saveValues(self):
        """
        Make a dictionary of variable values with the node and variable name
        keys
        """
        sd = dict()
        for node in self:
            sd[node] = OrderedDict()
            for var in self[node]:
                sd[node][var] = self[node][var].value
        return sd

    def loadValues(self, sd):
        """
        Load the variables values out of a dictionary
        """
        self.odict = None
        for node in sd:
            if node not in self:
                logging.getLogger("foqus." + __name__).debug(
                    "Cannot load variable node not in flowsheet, node:"
                    " {0} not in {1}".format(node, self.keys()))
                raise NodeVarListEx(2, msg=node)
            for var in sd[node]:
                self[node][var].value = sd[node][var]

    def saveDict(self):
        """
        Save the full variables list information to a dictionary
        """
        sd = dict()
        for node in self:
            sd[node] = OrderedDict()
            for var in self[node]:
                sd[node][var] = self[node][var].saveDict()
        return sd

    def loadDict(self, sd):
        """
        Load the full variable list innformation from a dict

        Args:
            sd: the dictionary with the stored information
        """
        self.clear()
        for node in sd:
            self.addNode(node)
            for var in sd[node]:
                self.addVariable(node, var).loadDict(sd[node][var])

    def scale(self):
        """
        Scale all the variables in the list
        """
        for key, NodeVars in self.iteritems():
            for vkey, var in NodeVars.iteritems():
                var.scale()

    def makeNaN(self):
        """
        Make all the variable values NaN
        """
        for key, NodeVars in self.iteritems():
            for vkey, var in NodeVars.iteritems():
                var.makeNaN()

    def count(self):
        """
        Return the number of variables
        """
        cn = self.compoundNames()
        return len(cn)

    def getFlat(self, names, scaled=False):
        """
        Return a flat list of variable values coresponding to a given list of
        names

        Args:
            names: A list of variable names to return node.var form
            scale: If true return scaled values
        """
        res = []
        if scaled:
            for name in names:
                self.get(name).scale()
                res.append(self.get(name).scaled)
        else:
            for name in names:
                res.append(self.get(name).value)
        return res

    def unflatten(self, nameList, valueList, unScale=False):
        """
        This takes a list of variable names, and a flat list of values. This
        function then un-flattens the values and creates a dictionary of
        variable values. The dictionary can be loaded.

        Args:
            nameList: a list of variable names. names are either node.var or a
                two-element list or tupple (node, var)
            valueList: a list of values for the variables
            unScale: the values are scaled so unscale them before putting in dict
        """
        sd = {}
        pos = 0
        for i, name in enumerate(nameList):
            if not isinstance(name, (list,tuple)):
                name = self.splitName(name)
            if not name[0] in sd:
                sd[name[0]] = {}
            sd[name[0]][name[1]] = valueList[pos]
            pos+=1
            if unScale:
                sd[name[0]][name[1]] = \
                    self[name[0]][name[1]].unscale2(sd[name[0]][name[1]])
        return sd


class NodeVars(object):
    """
    Class for variable attributes, variable scaling, and saving/loading.
    """
    def __init__(
        self,
        value=0.0,
        vmin=None,
        vmax=None,
        vdflt=None,
        unit="",
        vst="user",
        vdesc="",
        tags=[],
        dtype=float,
        dist=Distribution(Distribution.UNIFORM)
    ):
        """
        Initialize the variable list

        Args:
            value: variable value
            vmin: min value
            vmax: max value
            vdflt: default value
            unit: string description of units of measure
            vst: A sring description of a group for the variable {"user", "sinter"}
            vdesc: A sentence or so describing the variable
            tags: List of string tags for the variable
            dtype: type of data {float, int, str}
            dist: distribution type for UQ
        """
        self.dtype = dtype # type of data
        value = value
        if vmin is None:
            vmin = value
        if vmax is None:
            vmax = value
        if vdflt is None:
            vdflt = value
        self.min = vmin # maximum value
        self.max = vmax # minimum value
        self.default = vdflt # default value
        self.unit = unit # units of measure
        self.set = vst # variable set name user or sinter so I know if
                       # user added it or from sinter configuration file
        self.desc = vdesc # variable description
        self.scaled = 0.0 # scaled value for the variable
        self.scaling = 'None' # type of variable scaling
        self.minScaled = 0.0 # scaled minimum
        self.maxScaled = 0.0 # scaled maximum
        self.tags = tags # set of tags for use in heat integration or
                         # other searching and sorting
        self.con = False # true if the input is set through connection
        self.setValue(value) # value of the variable
        self.setType(dtype)
        self.dist = copy.copy(dist)

    def typeStr(self):
        """
        Convert the data type to a string for saving the variable to json
        """
        if self.dtype == float:
            return 'float'
        elif self.dtype == int:
            return 'int'
        elif self.dtype == str:
            return 'str'
        else:
            raise NodeVarEx(11, msg=str(dtype))

    def makeNaN(self):
        """
        Set the value to NaN
        """
        self.value = float('nan')

    def setType(self, dtype=float):
        """
        Convert from the current dtype to a new one.
        """
        if dtype == "float":
            dtype = float
        elif dtype == "int":
            dtype = int
        elif dtype == "str":
            dtype = str
        if not dtype in [float, int, str]:
            raise NodeVarEx(11, msg=str(dtype))
        self.dtype = dtype
        self.value = dtype(self.value)
        self.min = dtype(self.min)
        self.max = dtype(self.max)
        self.default = dtype(self.default)

    def setMin(self, val):
        """
        Set the minimum value
        """
        self.__min = self.dtype(val)

    def setMax(self, val):
        """
        Set the maximum value
        """
        self.__max = self.dtype(val)

    def setDefault(self, val):
        """
        Set the default value
        """
        self.__default = self.dtype(val)

    def setValue(self, val):
        """
        Set the variable value
        """
        self.__value = self.dtype(val)

    def __getattr__(self, name):
        """
        This should only be called if a variable doesn't have the attribute name.
        """
        if name == 'value':
            return self.__value
        elif name == 'min':
            return self.__min
        elif name == 'max':
            return self.__max
        elif name == 'default':
            return self.__default
        else:
            raise AttributeError

    def __setattr__(self, name, val):
        """
        This is called when setting an attribute, if the attribute is value,
        min, max, default, convert data type, otherwise do normal stuff
        """
        if name == 'value':
            self.setValue(val)
        elif name == 'min':
            self.setMin(val)
        elif name == 'max':
            self.setMax(val)
        elif name == 'default':
            self.setDefault(val)
        else:
            super(NodeVars, self).__setattr__(name, val)

    def scale(self):
        """
        Scale the value stored in the value field and put the result in the
        scaled field.
        """
        self.scaled = self.scale2(self.value)

    def unscale(self):
        """
        Unscale the value stored in the scaled field and put the result in the
        value field.
        """
        self.value = self.unscale2(self.scaled)

    def scaleBounds(self):
        """
        Calculate the scaled bounds and store the results in the minScaled and
        maxScaled fields.
        """
        self.minScaled = self.scale2(self.min)
        self.maxScaled = self.scale2(self.max)

    def scale2(self, val):
        """
        Use the variable's bounds and scale type to scale.  The scales all run
        from 0 at the minimum to 10 at the maximum, except None which does
        nothing.
        """
        try:
            if self.scaling == 'None':
                out = val
            elif self.scaling == 'Linear':
                out = 10*(val - self.min)/(self.max - self.min)
            elif self.scaling == 'Log':
                out = 10*(log10(val) - log10(self.min))/ \
                    (log10(self.max) - log10(self.min))
            elif self.scaling == 'Power':
                out = 10*(power(10, val) - power(10,self.min))/ \
                    (power(10, self.max) - power(10, self.min))
            elif self.scaling == 'Log 2':
                out = 10*log10(9*(val - self.min)/ \
                    (self.max - self.min)+1)
            elif self.scaling == 'Power 2':
                out = 10.0/9.0*(power(10,(val - self.min)/ \
                    (self.max - self.min))-1)
            else:
                raise
        except:
            raise NodeVarEx(
                code = 9,
                msg = "value = {0}, scaling method = {1}".format(val, self.scaling))
        return out

    def unscale2(self, val):
        """
        Convert value to an unscaled value using the variables settings.
        """
        try:
            if self.scaling == 'None':
                out = val
            elif self.scaling == 'Linear':
                out = val*(self.max - self.min)/10.0 + self.min
            elif self.scaling == 'Log':
                out = power(self.min*(self.max/self.min),(val/10.0))
            elif self.scaling == 'Power':
                out = log10((val/10.0)*(power(10,self.max) - \
                    power(10,self.min))+power(10, self.min))
            elif self.scaling == 'Log 2':
                out = (power(10, val/10.0)-1)*(self.max-self.min)/ \
                    9.0 + self.min
            elif self.scaling == 'Power 2':
                out = log10(9.0*val/10.0 + 1)*(self.max-self.min) + \
                    self.min
            else:
                raise
        except:
            raise NodeVarEx(
                code = 9,
                msg = "value = {0}, scaling method = {1}".\
                    format(val, self.scaling))
        return out

    def saveDict(self):
        """
        Save a variable's content to a dictionary. This is mostly used to save
        to a file but can also be used as an ugly way to make a copy of a
        variable.
        """
        sd = dict()
        vmin = self.min
        vmax = self.max
        vdefault = self.default
        value = self.value
        if self.dtype == float:
            sd["dtype"] = 'float'
        elif self.dtype == int:
            sd["dtype"] = 'int'
        elif self.dtype == str:
            sd["dtype"] = 'str'
        else:
            raise NodeVarEx(11, msg = str(dtype))
        sd["value"] = value
        sd["min"] = vmin
        sd["max"] = vmax
        sd["default"] = vdefault
        sd["unit"] = self.unit
        sd["set"] = self.set
        sd["desc"] = self.desc
        sd["scaling"] = self.scaling
        sd["tags"] = self.tags
        sd["dist"] = self.dist.saveDict()
        return sd

    def loadDict(self, sd):
        """
        Load the contents of a dictionary created by saveDict(), and possibly
        read back in as part of a json file.

        Args:
            sd: dict of data
        """
        assert isinstance(sd, dict)
        dtype = sd.get('dtype', 'float')
        if dtype == 'float':
            self.dtype = float
        elif dtype == 'int':
            self.dtype = int
        elif dtype == 'str':
            self.dtype = str
        else:
            raise NodeVarEx(11, msg=str(dtype))
        # Depending on how old the session file is, have history or value
        hist = sd.get("hist", None)
        value = sd.get("value", None)
        if hist is not None:
            self.value = hist[0]
        else:
            self.value = value
        self.min = sd.get("min", 0)
        self.max = sd.get("max", 0)
        self.default = sd.get("default", 0)
        self.unit = sd.get("unit", "")
        self.set = sd.get("set", "user")
        self.desc = sd.get("desc", "")
        self.scaling = sd.get("scaling", 'None')
        self.tags = sd.get("tags", [])
        dist = sd.get("dist", None)
        if dist is not None:
            self.dist.loadDict(dist)
        self.scale()
        self.scaleBounds()
