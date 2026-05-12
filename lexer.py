import ply.lex as lex

# ---------------------------------------------------------------------------
# Reserved keywords — the lexer maps matching identifiers to their token type
# ---------------------------------------------------------------------------
reserved = {
    'int':   'INT',
    'float': 'FLOAT',
    'double': 'DOUBLE',
    'char': 'CHAR',
    'void':  'VOID',
    'if':    'IF',
    'else':  'ELSE',
    'while': 'WHILE',
    'for':   'FOR',
    'print': 'PRINT',
    'return': 'RETURN',
}

tokens = [
    'ID', 'INT_LIT', 'FLOAT_LIT', 'STRING_LIT', 'CHAR_LIT',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'INCREMENT', 'DECREMENT',
    'AND', 'OR', 'NOT', 'AMP',
    'LE', 'GE', 'EQ', 'NE', 'LT', 'GT',
    'ASSIGN',
    'LPAREN', 'RPAREN',
    'LBRACE', 'RBRACE',
    'LBRACKET', 'RBRACKET',
    'SEMICOLON', 'COMMA',
] + list(reserved.values())

# ---------------------------------------------------------------------------
# Operators — function rules so multi-char operators are matched before
# their single-char prefixes (PLY adds function rules in source order)
# ---------------------------------------------------------------------------
def t_LE(t):
    r'<='
    return t

def t_GE(t):
    r'>='
    return t

def t_EQ(t):
    r'=='
    return t

def t_NE(t):
    r'!='
    return t

def t_INCREMENT(t):
    r'\+\+'
    return t

def t_DECREMENT(t):
    r'--'
    return t

def t_AND(t):
    r'&&'
    return t

def t_OR(t):
    r'\|\|'
    return t

def t_LT(t):
    r'<'
    return t

def t_GT(t):
    r'>'
    return t

def t_ASSIGN(t):
    r'='
    return t

# Simple single-character operators as string rules
t_PLUS      = r'\+'
t_MINUS     = r'-'
t_TIMES     = r'\*'
t_DIVIDE    = r'/'
t_MOD       = r'%'
t_NOT       = r'!'
t_AMP       = r'&'
t_LPAREN    = r'\('
t_RPAREN    = r'\)'
t_LBRACE    = r'\{'
t_RBRACE    = r'\}'
t_LBRACKET  = r'\['
t_RBRACKET  = r'\]'
t_SEMICOLON = r';'
t_COMMA     = r','

# ---------------------------------------------------------------------------
# Literals — float must be checked before int so "3.14" isn't split
# ---------------------------------------------------------------------------
def t_FLOAT_LIT(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

def t_STRING_LIT(t):
    r'"([^"\\]|\\.)*"'
    t.value = t.value[1:-1]
    return t

def t_CHAR_LIT(t):
    r"'([^'\\]|\\.)'"
    t.value = t.value[1:-1]
    return t

def t_INT_LIT(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

# ---------------------------------------------------------------------------
# Whitespace, newlines, comments
# ---------------------------------------------------------------------------
def t_COMMENT(t):
    r'//[^\n]*'
    pass  # discard line comments

def t_PREPROCESSOR(t):
    r'\#[^\n]*'
    pass

def t_BLOCK_COMMENT(t):
    r'/\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count('\n')
    pass

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

t_ignore = ' \t\r'

def t_error(t):
    message = f"  [Lexer] Illegal character '{t.value[0]}' at line {t.lexer.lineno}"
    if not hasattr(t.lexer, 'errors'):
        t.lexer.errors = []
    t.lexer.errors.append(message.strip())
    print(message)
    t.lexer.skip(1)

# ---------------------------------------------------------------------------
# Build the lexer
# ---------------------------------------------------------------------------
lexer = lex.lex()
lexer.errors = []
