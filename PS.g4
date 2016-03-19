grammar PS;

options {
    language=Python2;
}

WS: [ \t\r\n]+ -> skip;

ADD: '+';
SUB: '-';
MUL: '*';
DIV: '/';

L_PAREN: '(';
R_PAREN: ')';
L_BRACE: '{';
R_BRACE: '}';
L_BRACKET: '[';
R_BRACKET: ']';

BAR: '|';

FUNC_LIM:  '\\lim';
LIM_APPROACH_SYM: '\\to' | '\\rightarrow' | '\\Rightarrow';
FUNC_INT:  '\\int';
FUNC_SUM:  '\\sum';
FUNC_PROD: '\\prod';

FUNC_LOG:  '\\log';
FUNC_LN:   '\\ln';
FUNC_SIN:  '\\sin';
FUNC_COS:  '\\cos';
FUNC_TAN:  '\\tan';
FUNC_CSC:  '\\csc';
FUNC_SEC:  '\\sec';
FUNC_COT:  '\\cot';

FUNC_ARCSIN: '\\arcsin';
FUNC_ARCCOS: '\\arccos';
FUNC_ARCTAN: '\\arctan';
FUNC_ARCCSC: '\\arccsc';
FUNC_ARCSEC: '\\arcsec';
FUNC_ARCCOT: '\\arccot';

FUNC_SQRT: '\\sqrt';

CMD_TIMES: '\\times';
CMD_CDOT:  '\\cdot';
CMD_DIV:   '\\div';
CMD_FRAC:  '\\frac';

UNDERSCORE: '_';
CARET: '^';

DIFFERENTIAL: 'd' ([a-zA-Z] | '\\' [a-zA-Z]+);

LETTER: [a-zA-Z];
fragment DIGIT: [0-9];
NUMBER:
    DIGIT+ (',' DIGIT DIGIT DIGIT)*
    | DIGIT* (',' DIGIT DIGIT DIGIT)* '.' DIGIT+;

EQUAL: '=';
LT: '<';
LTE: '\\leq';
GT: '>';
GTE: '\\geq';

BANG: '!';

SYMBOL: '\\' [a-zA-Z]+;

math: relation;

relation:
    relation (EQUAL | LT | LTE | GT | GTE) relation
    | expr;

equality:
    expr EQUAL expr;

expr: additive;

additive:
    additive ADD additive
    | additive SUB additive
    | mp;

// mult part
mp:
    mp (MUL | CMD_TIMES | CMD_CDOT) mp
    | mp (DIV | CMD_DIV) mp
    | unary;

unary:
    (ADD | SUB) unary
    | postfix+;

postfix: exp postfix_op*;
postfix_op: BANG | eval_at;

eval_at:
    BAR (eval_at_sup | eval_at_sub | eval_at_sup eval_at_sub);

eval_at_sub:
    UNDERSCORE L_BRACE
    (expr | equality)
    R_BRACE;

eval_at_sup:
    CARET L_BRACE
    (expr | equality)
    R_BRACE;

exp:
    exp CARET (atom | L_BRACE expr R_BRACE) subexpr?
    | comp;

comp:
    group
    | abs_group
    | atom
    | frac
    | func;

group:
    L_PAREN expr R_PAREN 
    | L_BRACKET expr R_BRACKET;

abs_group: BAR expr BAR;

atom: (LETTER | SYMBOL) subexpr? | NUMBER | DIFFERENTIAL;

frac:
    CMD_FRAC L_BRACE
    (letter1=LETTER | (letter1=LETTER? upper=expr))
    R_BRACE L_BRACE
    (DIFFERENTIAL | lower=expr)
    R_BRACE;

func_normal:
    FUNC_LOG | FUNC_LN
    | FUNC_SIN | FUNC_COS | FUNC_TAN
    | FUNC_CSC | FUNC_SEC | FUNC_COT
    | FUNC_ARCSIN | FUNC_ARCCOS | FUNC_ARCTAN
    | FUNC_ARCCSC | FUNC_ARCSEC | FUNC_ARCCOT;

func:
    func_normal
    (subexpr? supexpr? | supexpr? subexpr?)
    func_arg

    | FUNC_INT
    (subexpr supexpr | supexpr subexpr)?
    (additive? DIFFERENTIAL | frac | additive)

    | FUNC_SQRT L_BRACE expr R_BRACE

    | (FUNC_SUM | FUNC_PROD)
    (subeq supexpr | supexpr subeq)
    mp
    | FUNC_LIM limit_sub mp;

limit_sub:
    UNDERSCORE L_BRACE
    (LETTER | SYMBOL)
    LIM_APPROACH_SYM
    expr (CARET L_BRACE (ADD | SUB) R_BRACE)?
    R_BRACE;

func_arg: atom+ | comp;

subexpr: UNDERSCORE L_BRACE expr R_BRACE;
supexpr: CARET L_BRACE expr R_BRACE;

subeq: UNDERSCORE L_BRACE equality R_BRACE;
supeq: UNDERSCORE L_BRACE equality R_BRACE;
