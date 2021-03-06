"""
This module defines the components for modified nodal analysis.  The components
are defined at the bottom of this file.

Copyright 2015--2019 Michael Hayes, UCECE

"""

from __future__ import print_function
from .cexpr import cExpr
from .omegaexpr import omegaExpr
from .symbols import j, omega, jomega
from .functions import sqrt
from .sym import capitalize_name, omegasym
from .grammar import delimiters
import lcapy
import inspect
import sys

module = sys.modules[__name__]

# TODO: ponder use of anonymous names when manipulating nets with select, zero, etc.


def arg_format(value):
    """Place value string inside curly braces if it contains a delimiter."""
    string = str(value)
    for delimiter in delimiters:
        if delimiter in string:
            return '{' + string + '}'
    return string


def _YZtype_select(expr, kind):
    """Return appropriate admittance/impedance value for analysis kind."""

    if kind in ('s', 'ivp', 'super'):
        return expr
    elif kind in ('dc', 'time'):
        return cExpr(expr.subs(0))
    elif isinstance(kind, str) and kind[0] == 'n':
        return expr(jomega)
    elif kind in (omegasym, omega):
        return expr(jomega)
    return omegaExpr(expr.subs(j * kind))
    

class Cpt(object):

    dependent_source = False
    independent_source = False    
    reactive = False
    need_branch_current = False
    need_extra_branch_current = False    
    need_control_current = False

    def __init__(self, cct, name, cpt_type, cpt_id, string,
                 opts_string, nodes, keyword, *args):

        self.cct = cct
        self.type = cpt_type
        self.id = cpt_id
        self.name = name
        self.relname = name
        self.namespace = ''
        self.nodes = nodes
        self.relnodes = nodes
        
        parts = name.split('.')
        if len(parts) > 1:
            self.namespace = '.'.join(parts[0:-1]) + '.'
            self.relname = parts[-1]
            self.relnodes = []
            for node in nodes:
                if node.startswith(self.namespace):
                    node = node[len(self.namespace):]
                self.relnodes.append(node)

        self.net = string.split(';')[0]
        # This is the initial opts_string from which the opts attribute
        # is derived.
        self.opts_string = opts_string
        self.args = args
        self.explicit_args = args        
        self.classname = self.__class__.__name__
        self.keyword = keyword
        self.opts = {}

        if self.type in ('W', 'O', 'P'):
            return

        if args is () or (self.type in ('F', 'H') and len(args) == 1):
            # Default value is the component name
            value = self.type
            if self.id != '':
                value += '_' + self.id

            if self.type in ('V', 'I') and keyword[1] == '':
                value = value[0].lower() + value[1:] + '(t)'

            args += (value, )
            self.args = args

        try:
            newclass = getattr(lcapy.oneport, self.classname)
        except:
            try:
                newclass = getattr(lcapy.twoport, self.classname)
            except:
                return
                
        self.cpt = newclass(*args)

    def __repr__(self):
        return self.__str__()

    def __str__(self):

        if self.opts == {}:
            return self.net
        return self.net + '; ' + str(self.opts)

    def stamp(self, cct):
        raise NotImplementedError('stamp method not implemented for %s' % self)

    def copy(self):
        """Make copy of net."""
        
        return str(self)
    
    def kill_initial(self):
        """Kill implicit sources due to initial conditions."""

        return self.copy()

    def kill(self):
        """Kill component."""

        raise ValueError('component not a source: %s' % self)

    def netmake(self, node_map=None, zero=False):
        """Create a new net description.  If node_map is not None,
        rename the nodes.  If zero is True, set args to zero."""

        string = self.name
        field = 0
        
        for node in self.relnodes:
            if node_map is not None:
                node = node_map[node]
            string += ' ' + node
            field += 1
            if field == self.keyword[0]:
                string += ' ' + self.keyword[1]
                field += 1                
        for arg in self.explicit_args:
            if zero:
                arg = 0
            string += ' ' + arg_format(arg)
            field += 1
            if field == self.keyword[0]:
                string += self.keyword[1]            
        string += '; %s' % self.opts
        return string
        
    def rename_nodes(self, node_map):
        """Rename the nodes using dictionary node_map."""

        return self.netmake(node_map)

    def select(self, kind=None):
        """Select domain kind for component."""

        raise ValueError('component not a source: %s' % self)    

    def zero(self):
        """Zero value of the voltage source.  This kills it but keeps it as a
        voltage source in the netlist.  This is required for dummy
        voltage sources that are required to specify the controlling
        current for CCVS and CCCS components."""        

        raise ValueError('component not a source: %s' % self)        

    def s_model(self, var):
        """Return s-domain model of component."""

        return self.copy()        

    def pre_initial_model(self):
        """Return pre-initial model of component."""

        return self.copy()        

    @property
    def is_causal(self):
        """Return True if causal component or if source produces
        a causal signal."""

        if self.cpt.voltage_source:
            return self.cpt.Voc.is_causal
        elif self.cpt.current_source:
            return self.cpt.Isc.is_causal
        else:
            raise ValueError('%s is not a source' % self)

    @property
    def is_dc(self):
        """Return True if source is dc."""
        
        if self.cpt.voltage_source:
            return self.cpt.Voc.is_dc
        elif self.cpt.current_source:
            return self.cpt.Isc.is_dc
        else:
            raise ValueError('%s is not a source' % self)

    @property
    def is_ac(self):
        """Return True if source is ac."""

        if self.cpt.voltage_source:
            return self.cpt.Voc.is_ac
        elif self.cpt.current_source:
            return self.cpt.Isc.is_ac
        else:
            raise ValueError('%s is not a source' % self)

    @property
    def has_s(self):
        """Return True if source has s-domain component."""

        if self.cpt.voltage_source:
            return self.cpt.Voc.has_s
        elif self.cpt.current_source:
            return self.cpt.Isc.has_s
        else:
            raise ValueError('%s is not a source' % self)        
        
    @property
    def is_noisy(self):
        """Return True if source is noisy."""

        if self.cpt.voltage_source:
            return self.cpt.is_noisy
        elif self.cpt.current_source:
            return self.cpt.is_noisy
        else:
            raise ValueError('%s is not a source' % self)        

    @property
    def zeroic(self):
        """Return True if initial conditions are zero (or unspecified)."""

        return self.cpt.zeroic

    @property
    def hasic(self):
        """Return True if initial conditions are specified."""

        return self.cpt.hasic

    @property
    def I(self):
        """Current through component."""

        return self.cct.get_I(self.name)

    @property
    def i(self):
        """Time-domain current through component."""

        return self.cct.get_i(self.name)

    @property
    def V(self):
        """Voltage drop across component."""

        return self.cct.get_Vd(self.nodes[0], self.nodes[1])

    @property
    def v(self):
        """Time-domain voltage drop across component."""

        return self.cct.get_vd(self.nodes[0], self.nodes[1])

    @property
    def Isc(self):
        """Short-circuit current."""

        return self.cpt.Isc.select(self.cct.kind)

    @property
    def Voc(self):
        """Open-circuit voltage."""

        return self.cpt.Voc.select(self.cct.kind)

    @property
    def Ys(self):
        """Admittance (s-domain)"""
        return self.cpt.Y

    @property
    def Zs(self):
        """Impedance (s-domain)"""
        return self.cpt.Z
    
    @property
    def Y(self):
        """Admittance"""

        return _YZtype_select(self.Ys, self.cct.kind)

    @property
    def Z(self):
        """Impedance"""

        return _YZtype_select(self.Zs, self.cct.kind)        


    @property
    def node_indexes(self):

        return (self.cct._node_index(n) for n in self.nodes)

    @property
    def branch_index(self):

        return self.cct._branch_index(self.name)

    def dummy_node(self):

        return '_' + self.cct._make_anon('node')


class Invalid(Cpt):
    
    @property
    def cpt(self):
         raise NotImplementedError('Invalid component for circuit analysis: %s' % self)       


class NonLinear(Invalid):

    def stamp(self, cct):
        raise NotImplementedError('Cannot analyse non-linear component: %s' % self)


class TimeVarying(Invalid):

    def stamp(self, cct):
        raise NotImplementedError('Cannot analyse time-varying component: %s' % self)


class Logic(Invalid):

    def stamp(self, cct):
        raise NotImplementedError('Cannot analyse logic component: %s' % self)


class Misc(Invalid):

    def stamp(self, cct):
        raise NotImplementedError('Cannot analyse misc component: %s' % self)


class Dummy(Cpt):

    causal = True
    dc = False
    ac = False
    zeroic = True
    hasic = None
    noisy = False

    
class IndependentSource(Cpt):

    independent_source = True
    
    def zero(self):
        """Zero value of the source.  For a voltage source this makes it a
        short-circuit; for a current source this makes it
        open-circuit.  This effectively kills the source but keeps it
        as a source in the netlist.  This is required for dummy
        voltage sources that are required to specify the controlling
        current for CCVS and CCCS components.

        """
        return self.netmake(zero=True)

class DependentSource(Dummy):

    dependent_source = True        
    
    def zero(self):
        """Zero value of the source.  For a voltage source this makes it a
        short-circuit; for a current source this makes it
        open-circuit.  This effectively kills the source but keeps it
        as a source in the netlist.  This is required for dummy
        voltage sources that are required to specify the controlling
        current for CCVS and CCCS components.

        """
        return self.netmake(zero=True)    

    
class RLC(Cpt):

    def s_model(self, var):

        if self.Voc == 0:        
            return '%sZ%s %s %s %s; %s' % (self.namespace, self.relname, 
                                           self.relnodes[0], self.relnodes[1],
                                           arg_format(self.Zs(var)), 
                                           self.opts)

        dummy_node = self.dummy_node()

        opts = self.opts.copy()

        # Strip voltage labels and save for open-circuit cpt
        # in parallel with Z and V.
        voltage_opts = opts.strip_voltage_labels()

        znet = '%sZ%s %s %s %s; %s' % (self.namespace, self.relname, 
                                       self.relnodes[0], dummy_node,
                                       arg_format(self.Zs(var)), 
                                       opts)

        # Strip voltage and current labels from voltage source.
        opts.strip_all_labels()

        vnet = '%sV%s %s %s s %s; %s' % (self.namespace, self.relname, 
                                         dummy_node, self.relnodes[1],
                                         arg_format(self.Voc.laplace()(var)),
                                         opts)

        if voltage_opts == {}:
            return znet + '\n' + vnet

        # Create open circuit in parallel to the Z and V
        # that has the voltage labels.
        opts = self.opts.copy()
        opts.strip_current_labels()
        # Need to convert voltage labels to s-domain.
        # v(t) -> V(s)
        # v_C -> V_C
        # v_L(t) -> V_L(s)
        for opt, val in voltage_opts.items():
            opts[opt] = capitalize_name(val)
            
        onet = '%sO%s %s %s; %s' % (self.namespace, self.relname, 
                                    self.relnodes[0], self.relnodes[1], opts)
        return znet + '\n' + vnet + '\n' + onet


class RC(RLC):

    def noisy(self):

        dummy_node = self.dummy_node()

        opts = self.opts.copy()

        rnet = '%s %s %s %s; %s' % (self.name, 
                                    self.relnodes[0], dummy_node,
                                    arg_format(self.args[0]),
                                    opts)
        
        Vn = 'sqrt(4 * k * T * %s)' % self.args[0]
        vnet = '%sVn%s %s %s noise %s; %s' % (
            self.namespace, self.relname, dummy_node,
            self.relnodes[1], arg_format(Vn), opts)
        return rnet + '\n' + vnet
    
    def stamp(self, cct):

        # L's can also be added with this stamp but if have coupling
        # it is easier to generate stamp that requires branch current
        # through the L.
        n1, n2 = self.node_indexes

        if self.type == 'C' and cct.kind == 'dc':
            Y = 0
        else:
            Y = self.Y.expr

        if n1 >= 0 and n2 >= 0:
            cct._G[n1, n2] -= Y
            cct._G[n2, n1] -= Y
        if n1 >= 0:
            cct._G[n1, n1] += Y
        if n2 >= 0:
            cct._G[n2, n2] += Y

        if cct.kind == 'ivp' and self.cpt.hasic and n1 >= 0:
            I = self.Isc.expr            
            cct._Is[n1] += I


class C(RC):

    reactive = True
    
    def kill_initial(self):
        """Kill implicit sources due to initial conditions."""
        return '%s %s %s %s; %s' % (
            self.name, self.relnodes[0], self.relnodes[1],
            arg_format(self.args[0]), self.opts)

    def pre_initial_model(self):

        if self.cpt.v0 == 0.0:
            return '%sO %s %s; %s' % (self.namespace, self.relnodes[0],
                                      self.relnodes[1], self.opts)
        return '%sV%s %s %s %s; %s' % (self.namespace, self.relname,
                                       self.relnodes[0], self.relnodes[1], 
                                       arg_format(self.cpt.v0), self.opts)


class E(DependentSource):
    """VCVS"""

    need_branch_current = True

    def stamp(self, cct):
        n1, n2, n3, n4 = self.node_indexes
        m = self.branch_index

        if n1 >= 0:
            cct._B[n1, m] += 1
            cct._C[m, n1] += 1
        if n2 >= 0:
            cct._B[n2, m] -= 1
            cct._C[m, n2] -= 1

        A = cExpr(self.args[0]).expr
        
        if n3 >= 0:
            cct._C[m, n3] -= A
        if n4 >= 0:
            cct._C[m, n4] += A

    def kill(self):
        newopts = self.opts.copy()
        newopts.strip_current_labels()
        newopts.strip_labels()

        return '%sW %s %s; %s' % (self.namespace, self.relnodes[0],
                                  self.relnodes[1], newopts)
            
class F(DependentSource):
    """CCCS"""

    need_control_current = True
    
    def stamp(self, cct):
        n1, n2 = self.node_indexes
        m = cct._branch_index(self.args[0])
        F = cExpr(self.args[1]).expr
            
        if n1 >= 0:
            cct._B[n1, m] -= F
        if n2 >= 0:
            cct._B[n2, m] += F

    def kill(self):
        newopts = self.opts.copy()
        newopts.strip_voltage_labels()
        newopts.strip_labels()

        return '%sO %s %s; %s' % (self.namespace, self.relnodes[0],
                                  self.relnodes[1], newopts)

class FB(Misc):
    """Ferrite bead"""
    pass


class G(DependentSource):
    """VCCS"""

    def stamp(self, cct):
        n1, n2, n3, n4 = self.node_indexes
        G = cExpr(self.args[0]).expr

        if n1 >= 0 and n3 >= 0:
            cct._G[n1, n3] -= G
        if n1 >= 0 and n4 >= 0:
            cct._G[n1, n4] += G
        if n2 >= 0 and n3 >= 0:
            cct._G[n2, n3] += G
        if n2 >= 0 and n4 >= 0:
            cct._G[n2, n4] -= G

    def kill(self):
        newopts = self.opts.copy()
        newopts.strip_voltage_labels()
        newopts.strip_labels()

        return '%sO %s %s; %s' % (self.namespace, self.relnodes[0],
                                  self.relnodes[1], newopts)

class GY(Dummy):
    """Gyrator"""    

    need_branch_current = True
    need_extra_branch_current = True

    def stamp(self, cct):
        
        n1, n2, n3, n4 = self.node_indexes
        m1 = self.cct._branch_index(self.name + 'X')
        m2 = self.branch_index

        # m1 is the input branch
        # m2 is the output branch
        # GY.I gives the current through the output branch

        # Could generalise to have different input and output
        # impedances, Z1 and Z2, but if Z1 != Z2 then the device is
        # not passive.

        # V2 = -I1 Z2     V1 = I2 Z1
        # where V2 = V[n1] - V[n2] and V1 = V[n3] - V[n4]
        
        Z1 = cExpr(self.args[0]).expr                    
        Z2 = Z1
        
        if n1 >= 0:
            cct._B[n1, m2] += 1
            cct._C[m1, n1] += 1
        if n2 >= 0:
            cct._B[n2, m2] -= 1
            cct._C[m1, n2] -= 1
        if n3 >= 0:
            cct._B[n3, m1] += 1
            cct._C[m2, n3] += 1
        if n4 >= 0:
            cct._B[n4, m1] -= 1
            cct._C[m2, n4] -= 1                        

        cct._D[m1, m1] += Z2
        cct._D[m2, m2] -= Z1


class H(DependentSource):
    """CCVS"""

    need_branch_current = True
    need_control_current = True

    def stamp(self, cct):
        n1, n2 = self.node_indexes
        m = self.branch_index

        if n1 >= 0:
            cct._B[n1, m] += 1
            cct._C[m, n1] += 1
        if n2 >= 0:
            cct._B[n2, m] -= 1
            cct._C[m, n2] -= 1
        
        mc = cct._branch_index(self.args[0])
        G = cExpr(self.args[1]).expr
        cct._D[m, mc] -= G

    def kill(self):
        newopts = self.opts.copy()
        newopts.strip_current_labels()
        newopts.strip_labels()

        return '%sW %s %s; %s' % (self.namespace, self.relnodes[0],
                                  self.relnodes[1], newopts)        

class I(IndependentSource):

    def select(self, kind=None):
        """Select domain kind for component."""

        return '%s %s %s %s; %s' % (
            self.name, self.relnodes[0], self.relnodes[1],
            self.cpt.Isc.netval(kind), self.opts)

    def kill(self):
        newopts = self.opts.copy()
        newopts.strip_voltage_labels()
        newopts.strip_labels()

        return '%sO %s %s; %s' % (self.namespace, self.relnodes[0],
                                  self.relnodes[1], newopts)

    def stamp(self, cct):

        n1, n2 = self.node_indexes

        I = self.Isc.expr

        if n1 >= 0:
            cct._Is[n1] += I
        if n2 >= 0:
            cct._Is[n2] -= I

    def s_model(self, var):

        return '%s %s %s s %s; %s' % (self.name, 
                                      self.nodes[0], self.nodes[1],
                                      arg_format(self.Isc.laplace()(var)),
                                      self.opts)

    def pre_initial_model(self):

        # Assume IC zero.  FIXME
        return '%sO %s %s; %s' % (self.namespace, self.relnodes[0],
                                  self.relnodes[1], self.opts)


class K(Cpt):
    
    def __init__(self, cct, name, cpt_type, cpt_id, string,
                 opts_string, nodes, keyword, *args):

        self.Lname1 = args[0]
        self.Lname2 = args[1]
        super (K, self).__init__(cct, name, cpt_type, cpt_id, string,
                                 opts_string, nodes, keyword, *args)

    def stamp(self, cct):

        if cct.kind == 'dc':
            return
        
        if cct.kind in ('t', 'time'):
            raise RuntimeError('Should not be evaluating mutual inductance in'
                               ' time domain')

        L1 = self.nodes[0]
        L2 = self.nodes[1]

        ZL1 = cct.elements[L1].Z
        ZL2 = cct.elements[L2].Z

        ZM = self.cpt.k * sqrt(ZL1 * ZL2).simplify()

        m1 = cct._branch_index(L1)
        m2 = cct._branch_index(L2)

        cct._D[m1, m2] += -ZM.expr
        cct._D[m2, m1] += -ZM.expr


class L(RLC):
    
    need_branch_current = True
    reactive = True

    def kill_initial(self):
        """Kill implicit sources due to initial conditions."""
        return '%s %s %s %s; %s' % (
            self.name, self.relnodes[0], self.relnodes[1],
            arg_format(self.args[0]), self.opts)

    def stamp(self, cct):

        # This formulation adds the inductor current to the unknowns

        n1, n2 = self.node_indexes
        m = self.branch_index

        if n1 >= 0:
            cct._B[n1, m] = 1
            cct._C[m, n1] = 1
        if n2 >= 0:
            cct._B[n2, m] = -1
            cct._C[m, n2] = -1

        if cct.kind == 'dc':
            Z = 0
        else:
            Z = self.Z.expr

        cct._D[m, m] += -Z

        if cct.kind == 'ivp' and self.cpt.hasic:
            V = self.Voc.expr            
            cct._Es[m] += V

    def pre_initial_model(self):

        if self.cpt.i0 == 0.0:
            return '%sW %s %s; %s' % (self.namespace, self.relnodes[0],
                                      self.relnodes[1], self.opts)
        return '%sI%s %s %s %s; %s' % (self.namespace, self.relname,
                                       self.relnodes[0], self.relnodes[1], 
                                       arg_format(self.cpt.i0), self.opts)

class O(Dummy):
    """Open circuit"""

    def stamp(self, cct):
        pass


class P(O):
    """Port"""
    pass


class R(RC):
    pass


class SPpp(Dummy):

    need_branch_current = True

    def stamp(self, cct):
        n1, n2, n3 = self.node_indexes
        m = self.branch_index

        if n3 >= 0:
            cct._B[n3, m] += 1
            cct._C[m, n3] += 1
        
        if n1 >= 0:
            cct._C[m, n1] -= 1
        if n2 >= 0:
            cct._C[m, n2] -= 1


class SPpm(Dummy):

    need_branch_current = True

    def stamp(self, cct):
        n1, n2, n3 = self.node_indexes
        m = self.branch_index

        if n3 >= 0:
            cct._B[n3, m] += 1
            cct._C[m, n3] += 1
        
        if n1 >= 0:
            cct._C[m, n1] -= 1
        if n2 >= 0:
            cct._C[m, n2] += 1

class SPppp(Dummy):

    need_branch_current = True

    def stamp(self, cct):
        n1, n2, n3, n4 = self.node_indexes
        m = self.branch_index

        if n3 >= 0:
            cct._B[n3, m] += 1
            cct._C[m, n3] += 1
        
        if n1 >= 0:
            cct._C[m, n1] -= 1
        if n2 >= 0:
            cct._C[m, n2] -= 1
        if n4 >= 0:
            cct._C[m, n4] -= 1

class SPpmm(Dummy):

    need_branch_current = True

    def stamp(self, cct):
        n1, n2, n3, n4 = self.node_indexes
        m = self.branch_index

        if n3 >= 0:
            cct._B[n3, m] += 1
            cct._C[m, n3] += 1
        
        if n1 >= 0:
            cct._C[m, n1] -= 1
        if n2 >= 0:
            cct._C[m, n2] += 1
        if n4 >= 0:
            cct._C[m, n4] += 1


class SPppm(Dummy):

    need_branch_current = True

    def stamp(self, cct):
        n1, n2, n3, n4 = self.node_indexes
        m = self.branch_index

        if n3 >= 0:
            cct._B[n3, m] += 1
            cct._C[m, n3] += 1
        
        if n1 >= 0:
            cct._C[m, n1] -= 1
        if n2 >= 0:
            cct._C[m, n2] -= 1
        if n4 >= 0:
            cct._C[m, n4] += 1


class TF(Cpt):
    """Transformer"""    

    need_branch_current = True

    def stamp(self, cct):

        n1, n2, n3, n4 = self.node_indexes
        m = self.branch_index

        if n1 >= 0:
            cct._B[n1, m] += 1
            cct._C[m, n1] += 1
        if n2 >= 0:
            cct._B[n2, m] -= 1
            cct._C[m, n2] -= 1
        
        T = self.cpt.alpha

        if n3 >= 0:
            cct._B[n3, m] -= T
            cct._C[m, n3] -= T
        if n4 >= 0:
            cct._B[n4, m] += T
            cct._C[m, n4] += T


class TFtap(Cpt):
    """Tapped transformer"""    

    def stamp(self, cct):
        raise NotImplementedError('Cannot analyse tapped transformer %s' % self)


class TL(Misc):
    """Transmission line"""

    # TODO
    pass


class TP(Misc):
    """Two port"""

    # TODO
    pass


class TR(Dummy):
    """Transfer function.  This is equivalent to a VCVS with the input and
    output referenced to node 0."""

    need_branch_current = True

    def stamp(self, cct):
        n1, n2 = self.node_indexes
        m = self.branch_index

        if n2 >= 0:
            cct._B[n2, m] += 1
            cct._C[m, n2] += 1
        
        A = cExpr(self.args[0]).expr
        
        if n1 >= 0:
            cct._C[m, n1] -= A


class V(IndependentSource):

    need_branch_current = True

    def select(self, kind=None):
        """Select domain kind for component."""

        return '%s %s %s %s; %s' % (
            self.name, self.relnodes[0], self.relnodes[1],
            self.cpt.Voc.netval(kind), self.opts)        

    def kill(self):
        newopts = self.opts.copy()
        newopts.strip_current_labels()
        newopts.strip_labels()

        return '%sW %s %s; %s' % (self.namespace, self.relnodes[0],
                                  self.relnodes[1], newopts)

    def stamp(self, cct):

        n1, n2 = self.node_indexes
        m = self.branch_index

        if n1 >= 0:
            cct._B[n1, m] += 1
            cct._C[m, n1] += 1
        if n2 >= 0:
            cct._B[n2, m] -= 1
            cct._C[m, n2] -= 1

        V = self.Voc.expr
        cct._Es[m] += V

    def s_model(self, var):

        return '%s %s %s s %s; %s' % (self.name, 
                                      self.relnodes[0], self.relnodes[1],
                                      arg_format(self.cpt.Voc.laplace()(var)),
                                      self.opts)

    def pre_initial_model(self):

        # Assume IC zero.  FIXME
        return '%sW %s %s; %s' % (self.namespace, self.relnodes[0],
                                  self.relnodes[1], self.opts)


class W(Dummy):
    """Wire"""

    def stamp(self, cct):
        pass


class XT(Misc):
    """Crystal"""

    reactive = True    


class Y(RC):
    """Admittance"""

    reactive = True


class Z(RC):
    """Impedance"""

    reactive = True    


classes = {}

def defcpt(name, base, docstring):
    
    if isinstance(base, str):
        base = classes[base]

    newclass = type(name, (base, ), {'__doc__': docstring})

    classes[name] = newclass


def make(classname, parent, name, cpt_type, cpt_id,
         string, opts_string, nodes, *args):

    # Create instance of component object
    newclass = classes[classname]

    # Switch context
    parent.context.switch()

    cpt = newclass(parent, name, cpt_type, cpt_id, string, opts_string, 
                   nodes, *args)
    # Add named attributes for the args?   Lname1, etc.

    # Restore context
    parent.context.restore()
        
    return cpt


# Dynamically create classes.
defcpt('AM', W, 'Ammeter')

defcpt('BAT', V, 'Battery')

defcpt('D', NonLinear, 'Diode')
defcpt('Dled', 'D', 'LED')
defcpt('Dphoto', 'D', 'Photo diode')
defcpt('Dschottky', 'D', 'Schottky diode')
defcpt('Dtunnel', 'D', 'Tunnel diode')
defcpt('Dzener', 'D', 'Zener diode')

defcpt('Eopamp', E, 'Opamp')
defcpt('Efdopamp', E, 'Fully differential opamp')

defcpt('sI', I, 's-domain current source')
defcpt('Isin', I, 'Sinusoidal current source')
defcpt('Idc', I, 'DC current source')
defcpt('Istep', I, 'Step current source')
defcpt('Iac', I, 'AC current source')
defcpt('Inoise', I, 'Noise current source')

defcpt('J', NonLinear, 'N JFET transistor')
defcpt('Jnjf', 'J', 'N JFET transistor')
defcpt('Jpjf', 'J', 'P JFET transistor')

defcpt('M', NonLinear, 'N MOSJFET transistor')
defcpt('Mnmos', 'M', 'N channel MOSJFET transistor')
defcpt('Mpmos', 'M', 'P channel MOSJFET transistor')
defcpt('MX', Misc, 'Mixer')

defcpt('Q', NonLinear, 'NPN transistor')
defcpt('Qpnp', 'Q', 'PNP transistor')
defcpt('Qnpn', 'Q', 'NPN transistor')

defcpt('Sbox', Misc, 'Box shape')
defcpt('Scircle', Misc, 'Circle shape')
defcpt('Sellipse', Misc, 'Ellipse shape')
defcpt('Striangle', Misc, 'Triangle shape')
defcpt('SW', TimeVarying, 'Switch')
defcpt('SWno', 'SW', 'Normally open switch')
defcpt('SWnc', 'SW', 'Normally closed switch')
defcpt('SWpush', 'SW', 'Pushbutton switch')
defcpt('SWspdt', 'SW', 'SPDT switch')

defcpt('TFcore', TF, 'Transformer with core')
defcpt('TFtapcore', TFtap, 'Transformer with core')

defcpt('Ubuffer', Logic, 'Buffer')
defcpt('Upbuffer', Logic, 'Buffer with power supplies')
defcpt('Uinverter', Logic, 'Inverter')
defcpt('Upinverter', Logic, 'Inverter with power supplies')
defcpt('Udiffamp', Misc, 'Differential amplifier')
defcpt('Uadc', Misc, 'ADC')
defcpt('Udac', Misc, 'DAC')
defcpt('Ubox', Misc, 'Box')
defcpt('Ucircle', Misc, 'Circle')
defcpt('Ubox4', Misc, 'Box')
defcpt('Ubox12', Misc, 'Box')
defcpt('Ucircle4', Misc, 'Circle')
defcpt('Uchip1310', Logic, 'General purpose chip')
defcpt('Uchip2121', Logic, 'General purpose chip')
defcpt('Uchip3131', Logic, 'General purpose chip')
defcpt('Uchip4141', Logic, 'General purpose chip')

defcpt('sV', V, 's-domain voltage source')
defcpt('Vsin', V, 'Sinusoidal voltage source')
defcpt('Vdc', V, 'DC voltage source')
defcpt('Vstep', V, 'Step voltage source')
defcpt('Vac', V, 'AC voltage source')
defcpt('Vnoise', V, 'Noise voltage source')

defcpt('VM', O, 'Voltmeter')

# Append classes defined in this module but not imported.
clsmembers = inspect.getmembers(module, lambda member: inspect.isclass(member) and member.__module__ == __name__)
for name, cls in clsmembers:
    classes[name] = cls

