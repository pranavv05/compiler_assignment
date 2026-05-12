import ply.yacc as yacc
from lexer import tokens, lexer   # tokens list required by PLY in this module
from ast_nodes import (
    Program, FunctionDef, Param, VarDecl, VarDeclList, ArrayDecl, Assign, BinOp, UnaryMinus, UnaryOp, PostfixOp,
    IntLit, FloatLit, StringLit, CharLit, Identifier, ArrayAccess,
    If, While, For, Print, Return, ExprStmt, FunctionCall, Block
)

# ---------------------------------------------------------------------------
# Operator precedence  (lowest → highest)
# IFX is a dummy token used to resolve the dangling-else shift/reduce conflict:
# giving ELSE higher precedence than IFX makes the parser shift on ELSE,
# attaching it to the nearest if.
# ---------------------------------------------------------------------------
precedence = (
    ('nonassoc', 'IFX'),
    ('nonassoc', 'ELSE'),
    ('left',     'OR'),
    ('left',     'AND'),
    ('left',     'EQ', 'NE'),
    ('left',     'LT', 'GT', 'LE', 'GE'),
    ('left',     'PLUS', 'MINUS'),
    ('left',     'TIMES', 'DIVIDE', 'MOD'),
    ('right',    'UMINUS', 'NOT', 'AMP'),
    ('left',     'INCREMENT', 'DECREMENT'),
)

# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------
def p_program(p):
    'program : external_list'
    p[0] = Program(p[1])

def p_external_list_multi(p):
    'external_list : external_list external'
    p[0] = p[1] + [p[2]]

def p_external_list_empty(p):
    'external_list : empty'
    p[0] = []

def p_external_function(p):
    'external : function_def'
    p[0] = p[1]

def p_external_stmt(p):
    'external : stmt'
    p[0] = p[1]

def p_stmt_list_multi(p):
    'stmt_list : stmt_list stmt'
    p[0] = p[1] + [p[2]]

def p_stmt_list_empty(p):
    'stmt_list : empty'
    p[0] = []

# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------
def p_stmt_var_decl(p):
    'stmt : var_decl'
    p[0] = p[1]

def p_stmt_array_decl(p):
    'stmt : array_decl'
    p[0] = p[1]

def p_stmt_assign(p):
    'stmt : assign_stmt'
    p[0] = p[1]

def p_stmt_if(p):
    'stmt : if_stmt'
    p[0] = p[1]

def p_stmt_while(p):
    'stmt : while_stmt'
    p[0] = p[1]

def p_stmt_for(p):
    'stmt : for_stmt'
    p[0] = p[1]

def p_stmt_print(p):
    'stmt : print_stmt'
    p[0] = p[1]

def p_stmt_return(p):
    'stmt : return_stmt'
    p[0] = p[1]

def p_stmt_expr(p):
    'stmt : expr_stmt'
    p[0] = p[1]

def p_stmt_block(p):
    'stmt : block'
    p[0] = p[1]

# ---------------------------------------------------------------------------
# Function definitions
# Supports normal C-style typed params and lenient old-style params:
#   int add(int a, int b) { ... }
#   int add(a, b) { ... }      # params default to int
# ---------------------------------------------------------------------------
def p_function_def_typed(p):
    'function_def : type ID LPAREN param_list RPAREN block'
    p[0] = FunctionDef(p[1], p[2], p[4], p[6], p.lineno(2))

def p_function_def_void(p):
    'function_def : VOID ID LPAREN param_list RPAREN block'
    p[0] = FunctionDef('void', p[2], p[4], p[6], p.lineno(2))

def p_param_list_multi(p):
    'param_list : param_list COMMA param'
    p[0] = p[1] + [p[3]]

def p_param_list_one(p):
    'param_list : param'
    p[0] = [p[1]]

def p_param_list_empty(p):
    'param_list : empty'
    p[0] = []

def p_param_typed(p):
    'param : type ID'
    p[0] = Param(p[2], p[1], p.lineno(2))

def p_param_untyped(p):
    'param : ID'
    p[0] = Param(p[1], 'int', p.lineno(1))

# ---------------------------------------------------------------------------
# Variable / array declarations
# ---------------------------------------------------------------------------
def p_var_decl(p):
    'var_decl : type declarator_list SEMICOLON'
    decls = []
    for name, init, lineno in p[2]:
        decls.append(VarDecl(p[1], name, init, lineno))
    p[0] = decls[0] if len(decls) == 1 else VarDeclList(decls)

def p_declarator_list_multi(p):
    'declarator_list : declarator_list COMMA declarator'
    p[0] = p[1] + [p[3]]

def p_declarator_list_one(p):
    'declarator_list : declarator'
    p[0] = [p[1]]

def p_declarator_init(p):
    'declarator : ID ASSIGN expr'
    p[0] = (p[1], p[3], p.lineno(1))

def p_declarator_plain(p):
    'declarator : ID'
    p[0] = (p[1], None, p.lineno(1))

def p_array_decl(p):
    'array_decl : type ID LBRACKET INT_LIT RBRACKET SEMICOLON'
    p[0] = ArrayDecl(p[1], p[2], p[4], p.lineno(2))

# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------
def p_assign_var(p):
    'assign_stmt : ID ASSIGN expr SEMICOLON'
    p[0] = Assign(Identifier(p[1], p.lineno(1)), p[3], p.lineno(1))

def p_assign_array(p):
    'assign_stmt : ID LBRACKET expr RBRACKET ASSIGN expr SEMICOLON'
    p[0] = Assign(ArrayAccess(p[1], p[3], p.lineno(1)), p[6], p.lineno(1))

# ---------------------------------------------------------------------------
# If / if-else
# ---------------------------------------------------------------------------
def p_if_else(p):
    'if_stmt : IF LPAREN expr RPAREN stmt ELSE stmt'
    p[0] = If(p[3], p[5], p[7], p.lineno(1))

def p_if_only(p):
    'if_stmt : IF LPAREN expr RPAREN stmt %prec IFX'
    p[0] = If(p[3], p[5], None, p.lineno(1))

# ---------------------------------------------------------------------------
# While
# ---------------------------------------------------------------------------
def p_while(p):
    'while_stmt : WHILE LPAREN expr RPAREN stmt'
    p[0] = While(p[3], p[5], p.lineno(1))

# ---------------------------------------------------------------------------
# For loop
# for ( for_init ; for_cond ; for_update ) stmt
# ---------------------------------------------------------------------------
def p_for(p):
    'for_stmt : FOR LPAREN for_init SEMICOLON for_cond SEMICOLON for_update RPAREN stmt'
    p[0] = For(p[3], p[5], p[7], p[9], p.lineno(1))

def p_for_init_decl(p):
    'for_init : type ID ASSIGN expr'
    p[0] = VarDecl(p[1], p[2], p[4], p.lineno(2))

def p_for_init_assign(p):
    'for_init : ID ASSIGN expr'
    p[0] = Assign(Identifier(p[1], p.lineno(1)), p[3], p.lineno(1))

def p_for_init_empty(p):
    'for_init : empty'
    p[0] = None

def p_for_cond_expr(p):
    'for_cond : expr'
    p[0] = p[1]

def p_for_cond_empty(p):
    'for_cond : empty'
    p[0] = None

def p_for_update_assign(p):
    'for_update : ID ASSIGN expr'
    p[0] = Assign(Identifier(p[1], p.lineno(1)), p[3], p.lineno(1))

def p_for_update_expr(p):
    'for_update : expr'
    p[0] = ExprStmt(p[1], getattr(p[1], 'lineno', 0))

def p_for_update_empty(p):
    'for_update : empty'
    p[0] = None

# ---------------------------------------------------------------------------
# Print
# ---------------------------------------------------------------------------
def p_print(p):
    'print_stmt : PRINT LPAREN expr RPAREN SEMICOLON'
    p[0] = Print(p[3], p.lineno(1))

# ---------------------------------------------------------------------------
# Return / expression statements
# ---------------------------------------------------------------------------
def p_return_value(p):
    'return_stmt : RETURN expr SEMICOLON'
    p[0] = Return(p[2], p.lineno(1))

def p_return_empty(p):
    'return_stmt : RETURN SEMICOLON'
    p[0] = Return(None, p.lineno(1))

def p_expr_stmt(p):
    'expr_stmt : expr SEMICOLON'
    p[0] = ExprStmt(p[1], getattr(p[1], 'lineno', 0))

# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def p_block(p):
    'block : LBRACE stmt_list RBRACE'
    p[0] = Block(p[2])

# ---------------------------------------------------------------------------
# Type keyword
# ---------------------------------------------------------------------------
def p_type_int(p):
    'type : INT'
    p[0] = 'int'

def p_type_float(p):
    'type : FLOAT'
    p[0] = 'float'

def p_type_double(p):
    'type : DOUBLE'
    p[0] = 'double'

def p_type_char(p):
    'type : CHAR'
    p[0] = 'char'

# ---------------------------------------------------------------------------
# Expressions (with precedence climbing via PLY's %prec)
# ---------------------------------------------------------------------------
def p_expr_binop(p):
    '''expr : expr PLUS   expr
            | expr MINUS  expr
            | expr TIMES  expr
            | expr DIVIDE expr
            | expr MOD    expr
            | expr AND    expr
            | expr OR     expr
            | expr LT     expr
            | expr GT     expr
            | expr LE     expr
            | expr GE     expr
            | expr EQ     expr
            | expr NE     expr'''
    p[0] = BinOp(p[2], p[1], p[3], p.lineno(2))

def p_expr_uminus(p):
    'expr : MINUS expr %prec UMINUS'
    p[0] = UnaryMinus(p[2], p.lineno(1))

def p_expr_not(p):
    'expr : NOT expr'
    p[0] = UnaryOp('!', p[2], p.lineno(1))

def p_expr_address(p):
    'expr : AMP expr'
    p[0] = UnaryOp('&', p[2], p.lineno(1))

def p_expr_postfix(p):
    '''expr : ID INCREMENT
            | ID DECREMENT'''
    p[0] = PostfixOp(p[2], Identifier(p[1], p.lineno(1)), p.lineno(1))

def p_expr_group(p):
    'expr : LPAREN expr RPAREN'
    p[0] = p[2]

def p_expr_function_call(p):
    'expr : ID LPAREN arg_list RPAREN'
    p[0] = FunctionCall(p[1], p[3], p.lineno(1))

def p_arg_list_multi(p):
    'arg_list : arg_list COMMA expr'
    p[0] = p[1] + [p[3]]

def p_arg_list_one(p):
    'arg_list : expr'
    p[0] = [p[1]]

def p_arg_list_empty(p):
    'arg_list : empty'
    p[0] = []

def p_expr_array_access(p):
    'expr : ID LBRACKET expr RBRACKET'
    p[0] = ArrayAccess(p[1], p[3], p.lineno(1))

def p_expr_id(p):
    'expr : ID'
    p[0] = Identifier(p[1], p.lineno(1))

def p_expr_int_lit(p):
    'expr : INT_LIT'
    p[0] = IntLit(p[1], p.lineno(1))

def p_expr_float_lit(p):
    'expr : FLOAT_LIT'
    p[0] = FloatLit(p[1], p.lineno(1))

def p_expr_string_lit(p):
    'expr : STRING_LIT'
    p[0] = StringLit(p[1], p.lineno(1))

def p_expr_char_lit(p):
    'expr : CHAR_LIT'
    p[0] = CharLit(p[1], p.lineno(1))

# ---------------------------------------------------------------------------
# Empty production
# ---------------------------------------------------------------------------
def p_empty(p):
    'empty :'
    p[0] = None

# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------
def p_error(p):
    if p:
        message = f"  [Parser] Syntax error at '{p.value}' (line {p.lineno})"
    else:
        message = "  [Parser] Syntax error at EOF"

    if 'parser' in globals() and hasattr(parser, 'errors'):
        parser.errors.append(message.strip())
    print(message)

# ---------------------------------------------------------------------------
# Build the parser (suppress table dump to keep output clean)
# ---------------------------------------------------------------------------
parser = yacc.yacc(debug=False, write_tables=False)
parser.errors = []
