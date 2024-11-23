import numpy as np
import os
import pdb

from decomp import decomp_lzd, decomp_p2d


class Sort:
    """Class Sort. This is the top class for all Signal types. Direct use is not recommended."""
    _ID = 0
    def __init__(self, name=None, module=None, dummy=False, buffer=None):
        """Initializes attributes of the signal

        :name: Name of the signal (default: automatic name generation)
        :module: Module-object, in which the signal lives (default: last created module)
        :dummy: True if it should not be added to a module (default: signal is added to module)
        :buffer: Number of buffers (registers) for the signal (default: 0)

        """
        if not name:
            self._name = f"sig{Sort._ID}"
            Sort._ID += 1
        else:
            self._name = name
        if not module:
            if len(Module.MODULE_STACK) == 0:
                raise Exception("There are no open modules")
            module = Module.MODULE_STACK[-1]
        self._module = module
        if not dummy:
            self._module.add_value(self)
        self._buffer = 0 if not buffer else buffer
        self._accessed = 0
        self._assigned = 0
        self._dummy = dummy
        self._internal_port=None
    def __str__(self):
        """Returns the name of the signal"""
        return str(self._name)
    def copy(self, name, module):
        """Returns a new copy of the signal"""
        return Sort(name=name, module=module)
    def _access(self, mode="VHDL", **args):
        """Creates a access for the signal. Behavior depends on the mode.

        mode = "VHDL":
            Returns an access string to the signal.
            If the Signal is buffered, the last buffer is returned.

        :mode: mode of the signal access. See above
        :returns: Returns an access to the signal

        """
        if self._buffer > 0:
            if "buffer" in args:
                buffer = args["buffer"]
                if buffer < 0 or buffer > self._buffer:
                    buffer = self._buffer
            else:
                buffer = self._buffer
            return f"b{buffer}_{self._name}"
        return self._name
    def _assign(self, mode="VHDL", **args):
        """Creates a assignment for the signal. Behavior depends on the mode.

        mode = "VHDL":
            Returns an assignment string to the signal.
            Assignment is always to buffer 0.

        :mode: mode of the signal assignment. See above
        :returns: Returns an assignment to the signal

        """
        if self._buffer > 0:
            if "buffer" in args:
                buffer = args["buffer"]
                if buffer < 0 or buffer > self._buffer:
                    buffer = self._buffer
            else:
                buffer = 0
            return f"b{buffer}_{self._name}"
        return self._name
    def assign(self, other):
        """Create an assignment of the other signal to this signal.
        Uses the AssignBlock class.
        
        :other: Other signal which should be assigned
        :returns: None
        """
        AssignBlock(self, other)
    def determine(self, **args):
        """Determine the properties of this signal. Not supported for the supertype"""
        pass
    def init(self, **args):
        """Init the initalisation strings for this signal. Not supported for the supertype"""
        pass
    def set_buffer(self, stages):
        """Sets the number of buffers (sequence of registers) for this signal.

        :stages: number of buffer stages
        :returns: None

        """
        self._buffer = stages
class Integer(Sort):
    """Signal type for Integers of a given bitwidth."""
    def __init__(self, width=None, **args):
        """Initializes attributes of the integer

        :width: bitwidth of the integer.

        """
        super().__init__(**args)
        self._width = width
        self._width_deps = []
        self._gens = []
        if self._width != None:
            self._determined = True
    def copy(self, name, module, new_width=None, assign_sig=False, mode="VHDL"):
        """Returns a new copy of the integer.

        :name: Name of the new integer
        :module: Module of the new integer
        :new_width: Width of the new integer (default: width of this integer)
        :assign_sig: If True, the current signal is assigned to the new signal.
        :mode: Mode for signal assignment (default is "VHDL")

        """
        if new_width != None:
            x = Integer(name=name, module=module, width=new_width)
        else:
            x = Integer(name=name, module=module, width=self._width)
        x._width_deps.append((self,0))
        self._width_deps.append((x,0))
        self._accessed += 1
        x._assigned += 1
        if assign_sig:
            if mode=="VHDL":
                x._gens.append((lambda a, b: f"{a._assign()} <= {b._access(upper=x._width-1)};", (x, self)))
        return x
    def generate(self):
        """Generator function for this signal. Used internally only."""
        return "\n".join([g[0](*g[1]) for g in self._gens])
    def determine(self, **args):
        """Derermines the width of the integer if possible. Used interanlly only."""
        others = args["others"] if "others" in args else {}
        others[self] = self._width
        for v, o in self._width_deps:
            if not (v in others):
                others = v.determine(others=others)
            if not others[self]:
                others[self] = others[v]+o if others[v] else None
            if others[v]:
                n = others[v] + o
                if not n == others[self]:
                    raise Exception(f"Integer width cannot be determined: {self._name}")
                others[self] = n
        self._width = others[self]
        return others
    def init(self, mode='VHDL'):
        """Init the initalisation strings for this signal and its buffers.
        Supported modes:
            mode = "VHDL": Generate initialization strings using VHDL syntax

        :mode: set mode for generation
        :returns: list of initialization strings.

        """
        if mode == 'VHDL':
            if self._buffer == 0:
                return [(self._name, f"std_logic_vector({self._width-1} downto 0)")]
            else:
                inits = []
                for i in range(self._buffer+1):
                    inits.append((f"b{i}_{self._name}", f"std_logic_vector({self._width-1} downto 0)"))
                return inits
    def _access(self, upper=None, lower=None, keep_vector=False, **args):
        """Creates a access for the signal. Behavior depends on the mode.

        mode = "VHDL":
            Returns an access string to the signal.
            If the Signal is buffered, the last buffer is returned.

        :mode: mode of the signal access. See above
        :upper: upper end of the vector access
        :lower: lower end of the vector access
        :keep_vector: True if the vector type should be maintained (Default: cast to lower type)
        :returns: Returns an access to the signal

        """
        if not self._width:
            raise Exception("Width has not been determined yet")
        if not upper!=None and not lower!=None:
            return super()._access(**args)
        if not upper!=None:
            upper = self._width-1
        if not lower!=None:
            lower = 0
        if upper >= self._width:
            raise Exception("Range is not valid")
        if lower < 0:
            raise Exception("Range is not valid")
        if upper-lower == 0 and not keep_vector:
            return super()._access(**args) + f"({lower})"
        return super()._access(**args) + f"({upper} downto {lower})"
    def _assign(self, upper=None, lower=None, **args):
        """Create an assignment of the other signal to this signal.
        Uses the AssignBlock class.

        mode = "VHDL":
            Returns an access string to the signal.
            If the Signal is buffered, the last buffer is returned.

        :mode: mode of the signal access. See above
        :other: Other signal which should be assigned
        :upper: upper end of the vector access
        :lower: lower end of the vector access
        :returns: None

        """
        if not self._width:
            raise Exception("Width has not been determined yet")
        if not upper!=None and not lower!=None:
            return super()._assign(**args)
        if not upper!=None:
            upper = self._width-1
        if not lower!=None:
            lower = 0
        if upper >= self._width:
            pdb.set_trace()
            raise Exception("Range is not valid")
        if lower < 0:
            raise Exception("Range is not valid")
        return super()._assign(**args) + f"({upper} downto {lower})"
    def add(self, other, long_name=False, name=None):
        """Generate an addition with another Ingteger. This operation is based on the Add2Block.
        A new signal for the result will be generated and the corresponding width restrictions set accordingly.

        result = self + other

        :other: other Integer object (second operand).
        :long_name: True if the name of the resulting signal should be descriptive (default: standard sigX naming)
        :name: name of the resulting signal (default: generated name)
        :returns: result integer

        """
        if long_name:
            r = Integer(name=f"{self._name}_plus_{other._name}", module=self._module, width=self._width)
        elif name != None:
            r = Integer(module=self._module, name=name, width=self._width)
        else:
            r = Integer(module=self._module, width=self._width)
        r._width_deps.append((self, 0))
        r._width_deps.append((other, 0))
        self._width_deps.append((r, 0))
        other._width_deps.append((r, 0))
        r._assigned += 1
        self._accessed += 1
        other._accessed += 1
        Add2Block(r, self, other, module=self._module)
        return r
    def complement(self, long_name=False, name=None):
        """Generate the complement of the integer (- this). This operation is baed on the ComplementBlock.
        A new signal for the result will be generated and the corresponding width restrictions set accordingly.

        result = 0 - self

        :long_name: True if the name of the resulting signal should be descriptive (default: standard sigX naming)
        :name: name of the resulting signal (default: generated name)
        :returns: result integer

        """
        if long_name:
            r = Integer(name=f"minus_{self._name}", module=self._module, width=self._width)
        elif name != None:
            r = Integer(module=self._module, name=name, width=self._width)
        else:
            r = Integer(module=self._module, width=self._width)
        r._width_deps.append((self, 0))
        self._width_deps.append((r, 0))
        r._assigned += 1
        self._accessed += 1
        ComplementBlock(r, self)
        return r
    def sub(self, other, long_name=False):
        """Generate a subtraction with another Ingteger. This operation is based on the Sub2Block.
        A new signal for the result will be generated and the corresponding width restrictions set accordingly.

        result = self - other

        :other: other Integer object (second operand).
        :long_name: True if the name of the resulting signal should be descriptive (default: standard sigX naming)
        :returns: result integer

        """
        if long_name:
            r = Integer(name=f"{self._name}_minus_{other._name}", module=self._module, width=self._width)
        else:
            r = Integer(module=self._module, width=self._width)
        r._width_deps.append((self, 0))
        r._width_deps.append((other, 0))
        self._width_deps.append((r, 0))
        other._width_deps.append((r, 0))
        r._assigned += 1
        self._accessed += 1
        other._accessed += 1
        Sub2Block(r, self, other, module=self._module)
        return r
    def mult(self, other, long_name=False):
        """Generate a multiplication with another Ingteger. This operation is based on the Mult2Block.
        A new signal for the result will be generated and the corresponding width restrictions set accordingly.
        The width of the result Integer will be twice the width of the input integers.

        result = self * other

        :other: other Integer object (second operand).
        :long_name: True if the name of the resulting signal should be descriptive (default: standard sigX naming)
        :returns: result integer

        """
        if long_name:
            r = Integer(name=f"{self._name}_mult_{other._name}", module=self._module, width=self._width*2)
        else:
            r = Integer(module=self._module, width=self._width*2)
        r._width_deps.append((self, self._width))
        r._width_deps.append((other, self._width))
        self._width_deps.append((r, self._width))
        other._width_deps.append((r, self._width))
        r._assigned += 1
        self._accessed += 1
        other._accessed += 1
        Mult2Block(r, self, other, module=self._module)
        return r
    def add3(self, other1, other2, sign1=1, sign2=1, long_name=False):
        """Generate an addition with two other Ingtegers. Functionality
        is based on the custom add8_3.vhd block. Currently, only VHDL mode
        is supported.
        A new signal for the result will be generated and the corresponding
        width restrictions set accordingly.
        
        result = self + sign1*other1 + sign2*other2

        :other1: first other Integer object (second operand).
        :other1: second other Integer object (third operand).
        :sign1: sign of other1 operand (1 oder -1) (default: 1)
        :sign2: sign of other2 operand (1 oder -1) (default: 1)
        :long_name: True if the name of the resulting signal should be descriptive (default: standard sigX naming)
        :returns: result integer

        """
        if long_name:
            r = Integer(name=f"{self._name}_plus_{other1._name}_plus_{other2._name}", module=self._module, width=self._width)
        else:
            r = Integer(module=self._module, width=self._width)
        if sign1 == 1 and sign2 == -1:
            beh = "add_subw"
        elif sign1 == -1 and sign2 == 1:
            beh = "add_subw"
            other1, other2 = other2, other1
        elif sign1 == -1 and sign2 == -1:
            beh = "sub_subw"
        else:
            beh = "add_addw"
        self._module.add_vhdl("add8_3w.vhd", {"width": self._width}, f"{r._name}_add3", signals={"a": self, "b": other1, "c": other2, "d": r}, behav=beh)
        self._accessed += 1
        other1._accessed += 1
        other2._accessed += 1
        r._assigned += 1
        self._width_deps.append((r, 0))
        other1._width_deps.append((r, 0))
        other2._width_deps.append((r, 0))
        r._width_deps.append((self, 0))
        r._width_deps.append((other1, 0))
        r._width_deps.append((other2, 0))
        return r
    def acc(sigs, tia=True, name=None):
        """Generates an adder tree for accumulation of several signals.
        This accumulation is based on Integer.add2 and Integer.add3
        New signals for the result and all intermediary steps will be
        generated and the corresponding width restrictions set accordingly.

        result = sum(sigs)

        :sigs: list of integers to accumulate
        :tia: False if three-input-adders (Integer.add3) should be disabled (default: TIA are enabled)
        :name: name for the result integer
        :returns: result integer (root of the adder-tree)

        """
        if len(sigs) == 0:
            raise Exception("Undefined empty accumulation")
        if len(sigs) == 1:
            return sigs[0]
        if len(sigs) == 2:
            return sigs[0].add(sigs[1])
        if len(sigs) == 3 and tia:
            return sigs[0].add3(sigs[1], sigs[2])
        else:
            left, right = sigs[:len(sigs)//2], sigs[len(sigs)//2:]
            r1 = Integer.acc(left, tia=tia)
            r2 = Integer.acc(right, tia=tia)
            r = Integer.add(r1,r2, name=name)
            return r
    def shift(self, positions, arith=True, long_name=False):
        """Generates a shift of this integer. This function uses the
        ShiftBlock.
        A new signal for the result will be generated and the
        corresponding width restrictions set accordingly.

        result = self << positions

        :positions: number of positions to shift
        :arith: False, if shifts shoud be logical only (default: arithmetic shifts)
        :long_name: True, if expressive integer names should be generated (default: sigX naming)
        :returns: result integer

        """
        if long_name:
            r = Integer(name=f"{self._name}_shift_{'m' if positions < 0 else ''}{abs(positions)}", module=self._module, width=self._width)
        else:
            r = Integer(module=self._module, width=self._width)
        r._assigned += 1
        self._accessed += 1
        r._width_deps.append((self, 0))
        self._width_deps.append((r, 0))

        if positions == 0:
            AssignBlock(r, self, module=self._module, force_name=f"shift 0")
        elif abs(positions) >= self._width:
            AssignBlock(r, Integer.constant(0, self._width, decimals=0, module=self._module), force_name=f"shift {positions}")
        else:
            ShiftBlock(r, self, positions, arith=arith)
    def constant(n, width, decimals, **args):
        """Returns an integer object, which is assigned the given contant value.
        If this function is called multiple times with the same arguments, the
        the same integer will be returned.

        :n: value for the constant integer
        :width: width of the constand integer
        :decimals: if applicable, decimals for the integer (fix-point)
        :returns: constant integer object

        """
        x = Integer(width=width, **args)
        n *= 2**decimals
        neg = n<0
        n = ("{0:0"+str(width) +"b}").format(int(abs(n)))
        if neg:
            n0 = n[:n.rfind("1")]
            n1 = n[n.rfind("1"):]
            n0 = "".join(["0" if x == "1" else "1" for x in n0])
            n = n0+n1
        x._assigned += 1
        x._gens.append((lambda a: f"{a._assign()} <= \"{n}\";", (x,)))
        return x
    def extend(self, width, arith=True, long_name=False):
        """Extends the bit-width of the integer. A new integer with the
        updated width will be created.
        Uses Integer.resize

        :width: width difference (positive -> larger width)
        :arith: False, if sign of the integer should not be considered (default: arithmetical extension with sign)
        :long_name: True, if expressive integer names should be generated (default: sigX naming)
        :returns: result integer

        """
        return self.resize(self._width+width, arith=arith, long_name=long_name, force_name=f"extend {width}")
    def shorten(self, width, arith=True, lower=0, long_name=False):
        """Shortens the bit-width of the integer. A new integer with the
        updated width will be created.
        Uses Integer.resize

        :width: width difference (positive -> smaller width)
        :arith: False, if sign of the integer should not be considered (default: arithmetical extension with sign)
        :lower: Number of bits cut from the lower end of the integer (default: 0)
        :long_name: True, if expressive integer names should be generated (default: sigX naming)
        :returns: result integer

        """
        return self.resize(self._width-width, arith=arith, long_name=long_name, force_name=f"shorten {width} from {lower}")
    def resize(self, width, arith=True, lower=0, long_name=False, force_name=None):
        """Resizes the bit-width of the integer. A new integer with the
        updated width will be created.
        Uses the ExtendBlock and ShortenBlock according to the widths.

        :width: absolute desired width
        :arith: False, if sign of the integer should not be considered (default: arithmetical extension with sign)
        :lower: Number of bits cut from the lower end of the integer (default: 0)
        :long_name: True, if expressive integer names should be generated (default: sigX naming)
        :force_name: force the name of the resulting integer. Should be used with care.
        :returns: result integer

        """
        if width == self._width:
            return self
        if long_name:
            r = Integer(width=width, name="{self._name}_resize{width}", module=self._module)
        else:
            r = Integer(width=width, module=self._module)
        r._assigned += 1
        self._accessed += 1
        if width > self._width:
            ExtendBlock(r, self, arith, module=self._module, force_name=force_name)
        else:
            ShortenBlock(r, self, arith, lower=lower, module=self._module, force_name=force_name)



class Block:
    """This is the super class for Blocks.
    Blocks represent the interconnection (pure or operational) between signals.
    """
    def __init__(self, name, inputs, outputs, module=None, **args):
        self._inputs = inputs
        self._outputs = outputs
        self._name = name
        if "force_name" in args:
            self._name = args["force_name"]
        if not module:
            if len(Module.MODULE_STACK) == 0:
                raise Exception("There are no open modules")
            module = Module.MODULE_STACK[-1]
        self._module = module
        self._module.add_block(self)
    def generateVHDL(self):
        """Generate VHDL for this block.

        :returns: string of VHDL assertions

        """
        raise Exception("Not Implemented")
class BinaryOpBlock(Block):
    """Super class for binary infix operations"""
    def __init__(self, name, result, operator, op1, op2, **args):
        super().__init__(name, [op1, op2], [result], **args)
        self._operator = operator
    def generateVHDL(self):
        return f"{self._outputs[0]._assign(mode='VHDL')} <= {self._inputs[0]._access(mode='VHDL')} {self._operator} {self._inputs[1]._access(mode='VHDL')};"
class BinarySignedOpBlock(Block):
    """Super class for binary infix operations with a cast to signed"""
    def __init__(self, name, result, operator, op1, op2, **args):
        super().__init__(name, [op1, op2], [result], **args)
        self._operator = operator
    def generateVHDL(self):
        return f"{self._outputs[0]._assign(mode='VHDL')} <= std_logic_vector(signed({self._inputs[0]._access(mode='VHDL')}) {self._operator} signed({self._inputs[1]._access(mode='VHDL')}));"
class UnaryOpBlock(Block):
    """Super class for unary prefix operations"""
    def __init__(self, name, result, operator, op, **args):
        super().__init__(name, [op], [result], **args)
        self._operator = operator
    def generateVHDL(self):
        return f"{self._outputs[0]._assign(mode='VHDL')} <= {self._operator} {self._inputs[0]._access(mode='VHDL')};"
class UnarySignedOpBlock(Block):
    """Super class for unary prefix operations with a cast to signed"""
    def __init__(self, name, result, operator, op, **args):
        super().__init__(name, [op], [result], **args)
        self._operator = operator
    def generateVHDL(self):
        return f"{self._outputs[0]._assign(mode='VHDL')} <= std_logic_vector({self._operator} signed({self._inputs[0]._access(mode='VHDL')}));"
class Add2Block(BinarySignedOpBlock):
    """Block for binary addition"""
    def __init__(self, result, op1, op2, **args):
        super().__init__("add2", result, '+', op1, op2, **args)
class Sub2Block(BinarySignedOpBlock):
    """Block for binary subtraction"""
    def __init__(self, result, op1, op2, **args):
        super().__init__("sub2", result, '-', op1, op2, **args)
class Mult2Block(BinarySignedOpBlock):
    """Block for binary multiplication"""
    def __init__(self, result, op1, op2, **args):
        super().__init__("mult2", result, '*', op1, op2, **args)
class And2Block(BinaryOpBlock):
    """Block for binary logical and"""
    def __init__(self, result, op1, op2, **args):
        super().__init__("and2", result, 'and', op1, op2, **args)
class Or2Block(BinaryOpBlock):
    """Block for binary logical or"""
    def __init__(self, result, op1, op2, **args):
        super().__init__("or2", result, 'or', op1, op2, **args)
class Xor2Block(BinaryOpBlock):
    """Block for binary logical xor"""
    def __init__(self, result, op1, op2, **args):
        super().__init__("xor2", result, 'xor', op1, op2, **args)
class Nand2Block(BinaryOpBlock):
    """Block for binary logical nand"""
    def __init__(self, result, op1, op2, **args):
        super().__init__("nand2", result, 'nand', op1, op2, **args)
class Nor2Block(BinaryOpBlock):
    """Block for binary logical nor"""
    def __init__(self, result, op1, op2, **args):
        super().__init__("nor2", result, 'nor', op1, op2, **args)
class NotBlock(UnaryOpBlock):
    """Block for unary logical not"""
    def __init__(self, result, op, **args):
        super().__init__("not", result, 'not', op, **args)
class ComplementBlock(UnarySignedOpBlock):
    """Block for unary copmlement"""
    def __init__(self, result, op, **args):
        super().__init__("comp", result, '-', op, **args)
class ShiftBlock(Block):
    """Block for shift operation"""
    def __init__(self, result, sig, positions, arith=True, **args):
        super().__init__(f"shift {positions}", [sig], [result], **args)
        self._positions = positions
        self._arith = arith
    def generateVHDL(self):
        sig = self._inputs[0]
        r = self._outputs[0]
        positions = self._positions
        if positions > 0:
            s = f"{r._assign(lower=positions)} <= {sig._access(upper=sig._width-positions-1, keep_vector=True)};\n"
            s += f"{r._assign(upper=positions-1)} <= (others => '0');"
            return s
        elif positions < 0:
            s = f"{r._assign(upper=r._width+positions-1)} <= {sig._access(lower=-positions, keep_vector=True)};\n"
            if self._arith:
                s += f"{r._assign(lower=r._width+positions)} <= (others => {sig._access(lower=sig._width-1)});"
            else:
                s += f"{r._assign(lower=r._width+positions)} <= (others => '0');"
            return s
class AssignBlock(Block):
    """Block for signal assignment"""
    def __init__(self, result, sig, **args):
        super().__init__("assign", [sig], [result], **args)
    def generateVHDL(self):
        return f"{self._outputs[0]._assign()} <= {self._inputs[0]._access()};"
class ExtendBlock(Block):
    """Block for signal width extention"""
    def __init__(self, result, sig, arith, **args):
        super().__init__(f"extend {result._width}", [sig], [result], **args)
        self._arith = arith
    def generateVHDL(self):
        b = self._outputs[0]
        a = self._inputs[0]
        s = f"{b._assign(upper=a._width-1)} <= {a._access()};\n"
        if self._arith:
            s += f"{b._assign(lower=a._width)} <= (others => {a._access(upper=a._width-1, lower=a._width-1)});"
        else:
            s += f"{b._assign(lower=a._width)} <= (others => '0');"
        return s
class ShortenBlock(Block):
    """Block for signal width shorten"""
    def __init__(self, result, sig, arith, lower, **args):
        super().__init__(f"shorten {result._width} from {lower}", [sig], [result], **args)
        self._arith = arith
        self._lower = lower
    def generateVHDL(self):
        b = self._outputs[0]
        a = self._inputs[0]
        lo = self._lower
        s = f"{b._assign()} <= {a._access(upper=b._width+lo-1, lower=lo)};\n"
        return s


class Module:
    """Class for Modules.
    Modules represent hardware units created with this framework.
    Similar to VHDL modules.
    
    Internally, modules are managed using a stack.
    """
    MODULE_STACK = []
    ENT_ID = 0
    OUTPATH = ""
    def __init__(self, name, dummy=False):
        """Constructor of the Module.

        :name: name of the module
        :dummy: True, if the created module should not be pushed to the stack.
        
        """
        self.values = []
        if not dummy:
            Module.MODULE_STACK.append(self)
        self._determined = False
        self._forced_ports = []
        self._ommited_ports = []
        self._entities = []
        self._module_name = name
        self._blocks = []
    def add_value(self, val):
        """Add a value (signal) to the module.

        :val: value to add
        :returns: None

        """
        self.values.append(val)
    def add_port(self, val, direction):
        """Add a value to the ports of the module.
        Usually, this is handled by the values themselves.

        :val: value to add
        :direction: direction of the port ("in", "out")
        :returns: None

        """
        if val not in self._forced_ports:
            self._forced_ports.append((val, direction))
    def add_block(self, block):
        """Add a block to the modules.
        See Block-class an its children.

        :block: block to add
        :returns: None

        """
        self._blocks.append(block)
    def remove_port(self, val):
        """Remove a value from the ports of this module.
        This does not change the port properties of the value itself.

        :val: value to add
        :returns: None

        """
        if val not in self._forced_ports:
            self._ommited_ports.append(val)
    def add_module(self, module, ent_name=None, signals={}, directions={}, behav=None):
        """Add another module to this module.
        Exising signals (values) can be directly connected by referencing them
        in the corresponding dictionary.
        All ports left unconnected will result in newly created signals.

        :module: Module-object to be instantiated
        :ent_name: label for the entity (e.g. for VHDL output) (default: generated label)
        :signals: dictionary of port connections (port_name: signal) (default: {})
        :directions: direction of the connected ports (default: {})
        :behav: Optional behavior of the module (e.g. for VHDL output) (default: None)
        :returns: list of new signals for new ports

        """
        if not ent_name:
            ent_name = f"ent{Module.ENT_ID}"
            Module.ENT_ID += 1
        ports = module.get_ports()
        ports = ports[0] + ports[1]
        connections = []
        new_signals = []
        for n, v in ports:
            if n != "clk":
                if n in signals:
                    connections.append((signals[n], n))
                    if n.startswith("pin") or n in directions and directions[n]=="in":
                        signals[n]._accessed += 1
                        signals[n]._internal_port = "in"
                    elif n.startswith("pout") or n in directions and directions[n]=="out":
                        signals[n]._assigned += 1
                        signals[n]._internal_port = "out"
                    continue
                new = v.copy(name=f"{ent_name}_{n}", module=self)
                if n.startswith("pin") or n in directions and directions[n]=="in":
                    new._accessed += 1
                    new._internal_port="in"
                elif n.startswith("pout") or n in directions and directions[n]=="out":
                    new._assigned += 1
                    new._internal_port="out"
                connections.append((new, n))
                new_signals.append(new)
            else:
                connections.append((n, n))
        self._entities.append((module, ent_name, [], connections, behav))
        return new_signals
    def add_vhdl(self, path, generic_values={}, ent_name=None, signals={}, behav=None):
        """Add another module to this module based on a VHDL description of the entity.
        Exising signals (values) can be directly connected by referencing them
        in the corresponding dictionary.
        All ports left unconnected will result in newly created signals.
        Parses the VHDL entity, creates a dummy module and uses add_module.

        :path: path to the VHDL file
        :generic_values: dictionary of generic values to be set (generic_name: value) (default: {})
        :ent_name: label for the entity (e.g. for VHDL output) (default: generated label)
        :signals: dictionary of port connections (port_name: signal) (default: {})
        :behav: Optional behavior of the module (e.g. for VHDL output) (default: None)
        :returns: list of new signals for new ports

        """
        content = " ".join(map(lambda x: x.strip(), filter(lambda x: len(x) > 0, map(lambda x: x if "--" not in x else x[:x.find("--")],open(path).read().split("\n")))))
        while not content.strip().startswith("entity "):
            content, _ = content[content.find(";")+2:], content[:content.find(";")]
        content = content[content.find(" "):].strip()
        vhdl_name = content[:content.find(" ")].strip()
        content = content[content.find(" "):].strip()
        content = content[content.find(" "):].strip()
        if content.startswith("generic"):
            content = content[content.find("(")+1:].strip()
            level = 1
            i = 0
            while level > 0:
                if content[i] == "(":
                    level += 1
                if content[i] == ")":
                    level -= 1
                i += 1
            i -= 1
            generics, content = content[:i], content[i:].strip()
            content = content[content.find(";")+1:].strip()
        else:
            generics = ""
        if content.startswith("port"):
            content = content[content.find("(")+1:].strip()
            level = 1
            i = 0
            while level > 0:
                if content[i] == "(":
                    level += 1
                if content[i] == ")":
                    level -= 1
                i += 1
            i -= 1
            ports, content = content[:i], content[i:].strip()
            ports = map(lambda x: x.strip(), ports.split(";"))
        else:
            ports = ""
        generics = map(lambda x: x.strip(), generics.split(";"))
        parsed_generics = []
        for generic in generics:
            parts = generic.split(":")
            if len(parts) != 2:
                continue
            name = parts[0].strip()
            sort = parts[1].strip()
            parsed_generics.append((name, sort))
        parsed_ports = []
        for port in ports:
            parts = port.split(":")
            if len(parts) != 2:
                continue
            name = parts[0].strip()
            parts = parts[1].strip().split(" ")
            direction = parts[0].strip()
            sort = " ".join(parts[1:]).strip()
            parsed_ports.append((name, direction, sort))
        m = VHDLModule(vhdl_name, parsed_generics, parsed_ports, generic_values)
        new_signals = self.add_module(m, ent_name, signals=signals, directions={n: d for n, d, _ in parsed_ports}, behav=behav)
        return new_signals
    def determine_signals(self):
        """Determines all values of this module"""
        others = {}
        if not self._determined:
            for v in self.values:
                others = v.determine(others=others)
            for v in self.values:
                if not v in others:
                    raise Exception(f"Integer width cannot be determined: {v._name}")
                v.determine(others={v:others[v]})
            self._determined = True
    def get_ports(self, mode="VHDL"):
        """Get all ports of this module. This includes both forced ports over self.add_port,
        and values that have port properties.

        :returns: tuple of lists: (list of ports, list of directions)

        """
        self.determine_signals()
        ports_all = []
        ports = ([], [])
        for v in self.values:
            if v in self._ommited_ports:
                continue
            if v._accessed == 0: # out port
                n, t = v.init(mode=mode)[-1]
                ports[0].append((f"pout_{n}", v))
                ports_all.append(v)
            elif v._assigned == 0: # in port
                n, t = v.init(mode=mode)[0]
                ports[1].append((f"pin_{n}", v))
                ports_all.append(v)
        for v,d in self._forced_ports:
            if v not in ports_all:
                if d == 'out':
                    n, t = v.init(mode=mode)[-1]
                else:
                    n, t = v.init(mode=mode)[0]
                ports[0 if d == "out" else 1].append((f"p{'out' if d == 'out' else 'in'}_{n}", v))
        return ports
    def generateVHDL(self):
        """Generates a VHDL description of this module in file "module.vhd".  """
        if len([v._name for v in self.values if v._width == None]) > 0:
            self.determine_signals()
        ports = []
        signals = ""
        content = ""
        ports_handled = []
        for v in self.values:
            if v in self._ommited_ports:
                continue
            if v._accessed == 0: # out port
                n, t = v.init()[-1]
                ports.append(f"pout_{n} : out {t}")
                content += f"pout_{n} <= {n};\n"
                ports_handled.append(v)
            elif v._assigned == 0: # in port
                n, t = v.init()[0]
                ports.append(f"pin_{n} : in {t}")
                content += f"{n} <= pin_{n};\n"
                ports_handled.append(v)
        for v,d in self._forced_ports:
            if not v in ports_handled:
                if d == 'out':
                    n, t = v.init()[-1]
                else:
                    n, t = v.init()[0]
                ports.append(f"p{'out' if d == 'out' else 'in'}_{n} : {'out' if d == 'out' else 'in'} {t}")
                if d == 'out':
                    content += f"pout_{n} <= {n}"
                else:
                    content += f"{n} <= pin_{n}"
                ports_handled.append(v)
        ports.append("clk : in std_logic")
        for v in self.values:
            for n, t in v.init(mode="VHDL"):
                signals += f"signal {n} : {t};\n"
        for v in self.values:
            s = v.generate()
            if len(s) > 0:
                content += v.generate() + "\n"
        ## buffers
        buffers = 0
        for v in self.values:
            for i in range(v._buffer):
                buffers += 1
        if buffers > 0:
            content += f"\n\n------------\n-- REGISTERS\n------------\n\n"
            content += "\nsync: process(clk)\nbegin\nif rising_edge(clk) then\n"
            for v in self.values:
                for i in range(v._buffer):
                    content += f"{v._assign(buffer=i+1)} <= {v._access(buffer=i)};\n"
            content += "end if;\nend process;\n"
        ## blocks
        content += "\n\n---------\n-- BLOCKS\n---------\n\n"
        for block in self._blocks:
            content += f"-- {block._name}\n{block.generateVHDL()}\n\n"
        ## entities
        for m, n, gs, cs, beh in self._entities:
            if beh == None:
                content += f"{n}: entity work.{m._module_name}\n"
            else:
                content += f"{n}: entity work.{m._module_name}({beh})\n"
            if len(gs) > 0:
                content += f"generic map ()"
            ts = lambda c, on: on.startswith("pin_") or c._internal_port=="in"
            content += f"port map ("
            content += f"{', '.join([f'{on} => {c._access() if ts(c,on) else c._assign()}' if c != 'clk' else 'clk' for c,on in cs])}"
            if type(m) != VHDLModule:
                content += ", clk => clk"
            content += ");\n"
        if not os.path.exists(os.path.join(os.getcwd(), Module.OUTPATH)):
            print(f"Creating output directory {Module.OUTPATH}")
            os.mkdir(os.path.join(os.getcwd(), Module.OUTPATH))
        print(f"Writing file {Module.OUTPATH}{self._module_name}.vhd")
        f = open(str(os.path.join(os.getcwd(), Module.OUTPATH, f"{self._module_name}.vhd")), "w")
        ts = ";\n"
        f.write("library IEEE;\nuse IEEE.std_logic_1164.ALL;\nuse IEEE.numeric_std.ALL;\n\n")
        f.write(f"entity {self._module_name} is\nport (\n{ts.join(ports)});\nend {self._module_name};\n\n")
        f.write(f"architecture beh of {self._module_name} is\n{signals}\nbegin\n")
        f.write(content)
        f.write("\nend beh;")
        f.close()
        Module.MODULE_STACK.pop()
class VHDLModule(Module):
    """Class for modules based on VHDL descriptions."""
    def __init__(self, name, generics, ports, generic_values):
        super().__init__(name, dummy=True)
        self._ports = ports
        self._generics = generics
        self._generic_values = generic_values
    def get_ports(self):
        ports = [[],[]] # list with in, out ports, name, signal
        for n, d, t in self._ports:
            if t.startswith("std_logic_vector") and t.endswith("downto 0)"):
                t = t[t.find("(")+1:]
                t = t[:t.find("downto")].strip()
                for g in self._generic_values:
                    t = t.replace(g, str(self._generic_values[g]))
                width = eval(t)+1
                t = Integer(width=width, dummy=True)
            ports[0 if d=='in' else 1].append((n, t))
        return ports


def gen_add2(W=8):
    """Test function which creates a add2 module."""
    mod = Module("add2")
    a = Integer(name="a", width=W)
    b = Integer(name="b", width=W)
    a.add(b)
    mod.generateVHDL()
    return mod
def gen_add3():
    """Test function which creates a add3 module."""
    mod = Module("add3")
    a = Integer(name="a", width=8)
    b = Integer(name="b", width=8)
    c = Integer(name="c", width=8)
    Integer.add3(a, b, c)
    mod.generateVHDL()
    return mod
