import time
import re
import sys
import antlr4
from antlr4.error.ErrorListener import ErrorListener

from gen.PSParser import PSParser
from gen.PSLexer import PSLexer
from gen.PSListener import PSListener

def process_sympy(sympy):

    matherror = MathErrorListener(sympy)

    stream = antlr4.InputStream(sympy)
    lex    = PSLexer(stream)
    lex.removeErrorListeners()
    lex.addErrorListener(matherror)

    tokens = antlr4.CommonTokenStream(lex)
    parser = PSParser(tokens)

    # remove default console error listener
    parser.removeErrorListeners()
    parser.addErrorListener(matherror)

    t0 = time.time()

    relation = parser.math().relation()
    sympy = stringify_relation(relation)

    t1 = time.time()
    return sympy

class MathErrorListener(ErrorListener):
    def __init__(self, src):
        super(ErrorListener, self).__init__()
        self.src = src

    def syntaxError(self, recog, symbol, line, col, msg, e):
        fmt = "%s\n%s\n%s"
        marker = "~" * col + "^"
        
        if msg.startswith("missing"):
            err = fmt % (msg, self.src, marker)
        elif msg.startswith("no viable"):
            err = fmt % ("I expected something else here", self.src, marker)
        elif msg.startswith("mismatched"):
            names = PSParser.literalNames
            expected = [names[i] for i in e.getExpectedTokens() if i < len(names)]
            if expected < 10:
                expected = " ".join(expected)
                err = (fmt % ("I expected one of these: " + expected,
                    self.src, marker))
            else:
                err = (fmt % ("I expected something else here", self.src, marker))
        else:
            err = fmt % ("I don't understand this", self.src, marker)
        raise Exception(err)

def stringify_relation(rel):
    if rel.expr():
        return stringify_expr(rel.expr())

    lh = stringify_relation(rel.relation(0))
    rh = stringify_relation(rel.relation(1))
    if rel.LT():
        fmt = "%s < %s"
    elif rel.LTE():
        fmt = "%s <= %s"
    elif rel.GT():
        fmt = "%s > %s"
    elif rel.GTE():
        fmt = "%s >= %s"
    elif rel.EQUAL():
        fmt = "%s = %s"
    return fmt % (lh, rh)

def stringify_expr(expr):
    return stringify_add(expr.additive())

def stringify_add(add):
    if add.ADD():
       lh = stringify_add(add.additive(0))
       rh = stringify_add(add.additive(1))
       return "%s + %s" % (lh, rh)
    elif add.SUB():
        lh = stringify_add(add.additive(0))
        rh = stringify_add(add.additive(1))
        return "%s - %s" % (lh, rh)
    else:
        return stringify_mp(add.mp())

def stringify_mult(mult):
    arr = map(stringify_mp, mult.mp())
    return "*".join(arr)

def stringify_mp(mp):
    if mp.MUL() or mp.CMD_TIMES() or mp.CMD_CDOT():
        lh = stringify_mp(mp.mp(0))
        rh = stringify_mp(mp.mp(1))
        return "%s * %s" % (lh, rh)
    elif mp.DIV() or mp.CMD_DIV():
        lh = stringify_mp(mp.mp(0))
        rh = stringify_mp(mp.mp(1))
        return "%s / %s" % (lh, rh)
    elif mp.unary():
        return stringify_unary(mp.unary())

def stringify_unary(unary):
    if unary.ADD():
        return "+%s" % (stringify_unary(unary.unary()))
    elif unary.SUB():
        return "-%s" % (stringify_unary(unary.unary()))
    elif unary.postfix():
        return stringify_postfix_list(unary.postfix())

def stringify_postfix_list(arr, i=0):
    if i >= len(arr):
        raise Exception("Index out of bounds")

    res = stringify_postfix(arr[i])
    if isinstance(res, basestring):
        if i == len(arr) - 1:
            return res # nothing to multiply by
        else:
            # multiply by next
            return res + "*" + stringify_postfix_list(arr, i + 1)
    else: # must be derivative
        wrt = res[0]
        if i == len(arr) - 1:
            raise Exception("Expected expression for derivative")
        else:
            expr = stringify_postfix_list(arr, i + 1)
            return "diff(%s, %s)" % (expr, wrt)

def stringify_postfix(postfix):
    exp = stringify_exp(postfix.exp())
    if postfix.BANG():
        if isinstance(exp, list):
            raise Exception("Cannot apply postfix to derivative")
        exp = "factorial(%s)" % (exp)
    return exp

def stringify_exp(exp):
    if exp.exp():
        base = stringify_exp(exp.exp(0))
        if isinstance(base, list):
            raise Exception("Cannot raise derivative to power")
        if exp.EXP():
            exponent = stringify_exp(exp.exp(1))
        elif exp.expr():
            exponent = stringify_expr(exp.expr())
        return "%s**(%s)" % (base, exponent)
    elif exp.comp():
        return stringify_comp(exp.comp())

def stringify_comp(comp):
    if comp.group():
        return "(%s)" % (stringify_expr(comp.group().expr()))
    elif comp.abs_group():
        return "Abs(%s)" % (stringify_expr(comp.abs_group().expr()))
    elif comp.atom():
        return stringify_atom(comp.atom())
    elif comp.frac():
        return stringify_frac(comp.frac())
    elif comp.func():
        return stringify_func(comp.func())

def stringify_atom(atom):
    if atom.LETTER():
        return atom.LETTER().getText()
    elif atom.SYMBOL():
        s = atom.SYMBOL().getText()[1:]
        if s == "infty":
            return "oo"
        else:
            return s
    elif atom.NUMBER():
        return atom.NUMBER().getText()
    elif atom.DIFFERENTIAL():
        return atom.DIFFERENTIAL().getText()

def stringify_frac(frac):
    if (frac.letter1 and frac.letter1.text == 'd' and frac.DIFFERENTIAL()):
        wrt = frac.DIFFERENTIAL().getText()[1:]
        if frac.expr(0):
            fmt = "diff(%s, %s)"
            return fmt % (stringify_expr(frac.expr(0)), wrt)
        else:
            return [wrt]

    num = ""
    if frac.letter1:
        num += frac.letter1.text
    if frac.upper:
        num += stringify_expr(frac.upper)
    denom = ""
    if frac.DIFFERENTIAL():
        denom += frac.DIFFERENTIAL().getText()
    if frac.lower:
        denom += stringify_expr(frac.lower)

    return "((%s) / (%s))" % (num, denom)

def stringify_func(func):
    if func.func_normal():
        name = func.func_normal().start.text[1:]

        # change arc<trig> -> a<trig>
        if (name=="arcsin" or name=="arccos" or name=="arctan"
            or name=="arccsc" or name=="arcsec" or name=="arccot"):
            name = "a" + name[3:]

        fmt = "%s(%s)"

        if (name=="log" or name=="ln") and func.subexpr():
            fmt += " / %s(%s)" % (name, stringify_expr(func.subexpr().expr()))

        if ((name=="sin" or name=="cos" or name=="tan" or name=="csc"
            or name=="sec" or name=="cot") and func.supexpr() and
            stringify_expr(func.supexpr().expr())=="-1"):
            name = "a" + name
        elif func.supexpr():
            fmt = (("(%s)" % fmt) + "**(" + 
                stringify_expr(func.supexpr().expr()) + ")")

        arg  = stringify_func_arg(func.func_arg())
        return fmt % (name, arg)
    elif func.FUNC_INT():
        return handle_integral(func)
    elif func.FUNC_SQRT():
        return "sqrt(%s)" % (stringify_expr(func.expr()))
    elif func.FUNC_SUM():
        return handle_sum_or_prod(func, "summation")
    elif func.FUNC_PROD():
        return handle_sum_or_prod(func, "product")

def stringify_func_arg(arg):
    if arg.comp():
        return stringify_comp(arg.comp())
    elif arg.atom():
        arr = map(stringify_atom, arg.atom())
        return "*".join(arr)

def handle_integral(func):
    if func.expr():
        integrand = stringify_expr(func.expr())
    else:
        integrand = stringify_mp(func.mp())

    if func.DIFFERENTIAL():
        int_var = func.DIFFERENTIAL().getText()[1:]
    else:
        m = re.search(r'(d[a-z])', integrand)
        if m:
            integrand = integrand.replace(m.group(0), '1')
            int_var = m.group(0)[1]
        else:
            # Assume dx by default
            int_var = "x"

    if func.subexpr():
        lower = stringify_expr(func.subexpr().expr())
        upper = stringify_expr(func.supexpr().expr())
        fmt = "integrate(%s, (%s, %s, %s))"
        return fmt % (integrand, int_var, lower, upper)
    else:
        fmt = "integrate(%s, %s)"
        return fmt % (integrand, int_var)

def handle_sum_or_prod(func, name):
    val      = stringify_mp(func.mp())
    iter_var = stringify_expr(func.subeq().equality().expr(0))
    start    = stringify_expr(func.subeq().equality().expr(1))
    end      = stringify_expr(func.supexpr().expr())

    fmt = "%s(%s, (%s, %s, %s))"
    return fmt % (name, val, iter_var, start, end)

def test_sympy():
    print process_sympy("e**(45 + 2)")
    print process_sympy("e + 5")
    print process_sympy("5 + e")
    print process_sympy("e")
    print process_sympy("\\frac{dx}{dy} \\int y x**(2) d y")
    print process_sympy("\\frac{dx}{dy} 5")
    print process_sympy("\\frac{d}{dx} \\int x**(2) d x")
    print process_sympy("\\frac{dx}{dy} \\int x**(2) d x")
    print process_sympy("\\frac{d}{dy} x**(2) + x y = 0")
    print process_sympy("\\frac{d}{dy} x**(2) + x y = 2")
    print process_sympy("\\frac{d x**(3)}{dy}")
    print process_sympy("\\frac{d x**(3)}{dy} + x**3")
    print process_sympy("\\int^{5x}_{2} x**(2) d y")
    print process_sympy("\\int_{5x}^{2} x^{2} d x")
    print process_sympy("\\int x^{2} d x")
    print process_sympy("2 4 5 - 2 3 1")

if __name__ == "__main__":
    test_sympy()
