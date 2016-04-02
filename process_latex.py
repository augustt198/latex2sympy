import sympy
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


    relation = parser.math().relation()
    expr = convert_relation(relation)

    return expr

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

def convert_relation(rel):
    if rel.expr():
        return convert_expr(rel.expr())

    lh = convert_relation(rel.relation(0))
    rh = convert_relation(rel.relation(1))
    if rel.LT():
        return sympy.StrictLessThan(lh, rh)
    elif rel.LTE():
        return sympy.LessThan(lh, rh)
    elif rel.GT():
        return sympy.StrictGreaterThan(lh, rh) 
    elif rel.GTE():
        return sympy.GreaterThan(lh, rh)
    elif rel.EQUAL():
        return sympy.Eq(lh, rh)

def convert_expr(expr):
    return convert_add(expr.additive())

def convert_add(add):
    if add.ADD():
       lh = convert_add(add.additive(0))
       rh = convert_add(add.additive(1))
       return sympy.Add(lh, rh, evaluate=False)
    elif add.SUB():
        lh = convert_add(add.additive(0))
        rh = convert_add(add.additive(1))
        return sympy.Add(lh, -1 * rh, evaluate=False)
    else:
        return convert_mp(add.mp())

def convert_mult(mult):
    arr = map(convert_mp, mult.mp())
    return sympy.Mul(*arr)

def convert_mp(mp):
    if mp.MUL() or mp.CMD_TIMES() or mp.CMD_CDOT():
        lh = convert_mp(mp.mp(0))
        rh = convert_mp(mp.mp(1))
        return sympy.Mul(lh, rh, evaluate=False)
    elif mp.DIV() or mp.CMD_DIV():
        lh = convert_mp(mp.mp(0))
        rh = convert_mp(mp.mp(1))
        return sympy.Mul(lh, sympy.Pow(rh, -1, evaluate=False), evaluate=False)
    elif mp.unary():
        return convert_unary(mp.unary())

def convert_unary(unary):
    if unary.ADD():
        return convert_unary(unary.unary())
    elif unary.SUB():
        return sympy.Mul(-1, convert_unary(unary.unary()), evaluate=False)
    elif unary.postfix():
        return convert_postfix_list(unary.postfix())

def convert_postfix_list(arr, i=0):
    if i >= len(arr):
        raise Exception("Index out of bounds")

    res = convert_postfix(arr[i])
    if isinstance(res, sympy.Expr):
        if i == len(arr) - 1:
            return res # nothing to multiply by
        else:
            if i > 0:
                left_syms  = convert_postfix(arr[i - 1]).atoms(sympy.Symbol)
                right_syms = convert_postfix(arr[i + 1]).atoms(sympy.Symbol)
                # if the left and right sides contain no variables and the
                # symbol in between is 'x', treat as multiplication.
                if len(left_syms) == 0 and len(right_syms) == 0 and str(res) == "x":
                    return convert_postfix_list(arr, i + 1)
            # multiply by next
            return sympy.Mul(res, convert_postfix_list(arr, i + 1), evaluate=False)
    else: # must be derivative
        wrt = res[0]
        if i == len(arr) - 1:
            raise Exception("Expected expression for derivative")
        else:
            expr = convert_postfix_list(arr, i + 1)
            return sympy.Derivative(expr, wrt)

def do_subs(expr, at):
    if at.expr():
        at_expr = convert_expr(at.expr())
        syms = at_expr.atoms(sympy.Symbol)
        if len(syms) == 0:
            return expr
        elif len(syms) > 0:
            sym = next(iter(syms))
            return expr.subs(sym, at_expr)
    elif at.equality():
        lh = convert_expr(at.equality().expr(0))
        rh = convert_expr(at.equality().expr(1))
        return expr.subs(lh, rh)

def convert_postfix(postfix):
    exp = convert_exp(postfix.exp())
    for op in postfix.postfix_op():
        if op.BANG():
            if isinstance(exp, list):
                raise Exception("Cannot apply postfix to derivative")
            exp = sympy.factorial(exp, evaluate=False)
        elif op.eval_at():
            ev = op.eval_at()
            at_b = None
            at_a = None
            if ev.eval_at_sup():
                at_b = do_subs(exp, ev.eval_at_sup()) 
            if ev.eval_at_sub():
                at_a = do_subs(exp, ev.eval_at_sub())
            if at_b != None and at_a != None:
                exp = sympy.Add(at_b, -1 * at_a, evaluate=False)
            elif at_b != None:
                exp = at_b
            elif at_a != None:
                exp = at_a
            
    return exp

def convert_exp(exp):
    if exp.exp():
        base = convert_exp(exp.exp())
        if isinstance(base, list):
            raise Exception("Cannot raise derivative to power")
        if exp.atom():
            exponent = convert_atom(exp.atom())
        elif exp.expr():
            exponent = convert_expr(exp.expr())
        return sympy.Pow(base, exponent, evaluate=False)
    elif exp.comp():
        return convert_comp(exp.comp())

def convert_comp(comp):
    if comp.group():
        return convert_expr(comp.group().expr())
    elif comp.abs_group():
        return sympy.Abs(convert_expr(comp.abs_group().expr()))
    elif comp.atom():
        return convert_atom(comp.atom())
    elif comp.frac():
        return convert_frac(comp.frac())
    elif comp.func():
        return convert_func(comp.func())

def convert_atom(atom):
    if atom.LETTER():
        return sympy.Symbol(atom.LETTER().getText())
    elif atom.SYMBOL():
        s = atom.SYMBOL().getText()[1:]
        if s == "infty":
            return sympy.oo
        else:
            return sympy.Symbol(s)
    elif atom.NUMBER():
        s = atom.NUMBER().getText().replace(",", "")
        return sympy.Number(s)
    elif atom.DIFFERENTIAL():
        var = get_differential_var(atom.DIFFERENTIAL())
        return sympy.Symbol('d' + var.name)

def convert_frac(frac):
    if (frac.letter1 and frac.letter1.text == 'd' and frac.DIFFERENTIAL()):
        wrt = get_differential_var(frac.DIFFERENTIAL())
        if frac.expr(0):
            return sympy.Derivative(convert_expr(frac.expr(0)), wrt)
        else:
            return [wrt]

    num = 1
    if frac.letter1:
        num = sympy.Symbol(frac.letter1.text)
    if frac.upper:
        upper = convert_expr(frac.upper)
        tok = frac.upper.start.text
        if tok == "+" or tok == "-":
            num = sympy.Add(num, upper, evaluate=False)
        else:
            num = sympy.Mul(num, upper, evaluate=False)
        
    if frac.DIFFERENTIAL():
        text = frac.DIFFERENTIAL().getText()
        first = sympy.Symbol(text[0])
        second = get_differential_var(frac.DIFFERENTIAL())
        denom = sympy.Mul(first, second, evaluate=False)
    if frac.lower:
        denom = convert_expr(frac.lower)

    return sympy.Mul(num, sympy.Pow(denom, -1, evaluate=False), evaluate=False)

def convert_func(func):
    if func.func_normal():
        arg = convert_func_arg(func.func_arg())
        name = func.func_normal().start.text[1:]

        # change arc<trig> -> a<trig>
        if name in ["arcsin", "arccos", "arctan", "arccsc", "arcsec",
        "arccot"]:
            name = "a" + name[3:]
            expr = getattr(sympy.functions, name)(arg)
            
        fmt = "%s(%s)"

        if (name=="log" or name=="ln"):
            if func.subexpr():
                base = convert_expr(func.subexpr().expr())
            elif name == "log":
                base = 10
            elif name == "ln":
                base = sympy.E

            expr = sympy.log(arg, base)

        if name in ["sin", "cos", "tan", "csc", "sec", "cot"]:
            if func.supexpr() and convert_expr(func.supexpr().expr()) == -1:
                name = "a" + name
                expr = getattr(sympy.functions, name)(arg)
            else:
                expr = getattr(sympy.functions, name)(arg)
                if func.supexpr():
                    power = convert_expr(func.supexpr().expr())
                    expr = sympy.Pow(expr, power)

        return expr
    elif func.FUNC_INT():
        return handle_integral(func)
    elif func.FUNC_SQRT():
        expr = convert_expr(func.base)
        if func.root:
            r = convert_expr(func.root)
            return sympy.root(expr, r)
        else:
            return sympy.sqrt(expr)
    elif func.FUNC_SUM():
        return handle_sum_or_prod(func, "summation")
    elif func.FUNC_PROD():
        return handle_sum_or_prod(func, "product")
    elif func.FUNC_LIM():
        return handle_limit(func)

def convert_func_arg(arg):
    if arg.comp():
        return convert_comp(arg.comp())
    elif arg.atom():
        arr = map(convert_atom, arg.atom())
        return sympy.Mul(*arr)

def handle_integral(func):
    if func.additive():
        integrand = convert_add(func.additive())
    elif func.frac():
        integrand = convert_frac(func.frac())
    else:
        integrand = 1

    int_var = None
    if func.DIFFERENTIAL():
        int_var = get_differential_var(func.DIFFERENTIAL())
    else:
        for sym in integrand.atoms(sympy.Symbol):
            s = str(sym)
            if len(s) > 1 and s[0] == 'd':
                if s[1] == '\\':
                    int_var = sympy.Symbol(s[2:])
                else:
                    int_var = sympy.Symbol(s[1:])
                int_sym = sym
        if int_var:
            integrand = integrand.subs(int_sym, 1)
        else:
            # Assume dx by default
            int_var = sympy.Symbol('x')

    if func.subexpr():
        if func.subexpr().atom():
            lower = convert_atom(func.subexpr().atom())
        else:
            lower = convert_expr(func.subexpr().expr())
        if func.supexpr().atom():
            upper = convert_atom(func.supexpr().atom())
        else:
            upper = convert_expr(func.supexpr().expr())
        return sympy.Integral(integrand, (int_var, lower, upper))
    else:
        return sympy.Integral(integrand, int_var)

def handle_sum_or_prod(func, name):
    val      = convert_mp(func.mp())
    iter_var = convert_expr(func.subeq().equality().expr(0))
    start    = convert_expr(func.subeq().equality().expr(1))
    end      = convert_expr(func.supexpr().expr())

    if name == "summation":
        return sympy.Sum(val, (iter_var, start, end))
    elif name == "product":
        return sympy.Product(val, (iter_var, start, end))

def handle_limit(func):
    sub = func.limit_sub()
    if sub.LETTER():
        var = sympy.Symbol(sub.LETTER().getText())
    elif sub.SYMBOL():
        var = sympy.Symbol(sub.SYMBOL().getText()[1:])
    else:
        var = sympy.Symbol('x')
    if sub.SUB():
        direction = "-"
    else:
        direction = "+"
    approaching = convert_expr(sub.expr())
    content     = convert_mp(func.mp())
    
    return sympy.Limit(content, var, approaching, direction)

def get_differential_var(d):
    text = d.getText()
    for i in range(1, len(text)):
        c = text[i]
        if not (c == " " or c == "\r" or c == "\n" or c == "\t"):
            idx = i
            break
    text = text[idx:]
    if text[0] == "\\":
        text = text[1:]
    return sympy.Symbol(text)

def test_sympy():
    print process_sympy("e**(45 + 2)")
    print process_sympy("e + 5")
    print process_sympy("5 + e")
    print process_sympy("e")
    print process_sympy("\\frac{dx}{dy} \\int y x**(2) dy")
    print process_sympy("\\frac{dx}{dy} 5")
    print process_sympy("\\frac{d}{dx} \\int x**(2) dx")
    print process_sympy("\\frac{dx}{dy} \\int x**(2) dx")
    print process_sympy("\\frac{d}{dy} x**(2) + x y = 0")
    print process_sympy("\\frac{d}{dy} x**(2) + x y = 2")
    print process_sympy("\\frac{d x**(3)}{dy}")
    print process_sympy("\\frac{d x**(3)}{dy} + x**3")
    print process_sympy("\\int^{5x}_{2} x**(2) dy")
    print process_sympy("\\int_{5x}^{2} x^{2} dx")
    print process_sympy("\\int x^{2} dx")
    print process_sympy("2 4 5 - 2 3 1")

if __name__ == "__main__":
    test_sympy()
