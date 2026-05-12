from ast_nodes import (
    Program, FunctionDef, Param, VarDecl, VarDeclList, ArrayDecl, Assign, BinOp, UnaryMinus, UnaryOp, PostfixOp,
    IntLit, FloatLit, StringLit, CharLit, Identifier, ArrayAccess,
    If, While, For, Print, Return, ExprStmt, FunctionCall, Block
)


# ---------------------------------------------------------------------------
# Symbol table
# ---------------------------------------------------------------------------
class SymbolTable:
    def __init__(self):
        self.scopes = [{}]     # stack; index 0 = global scope
        self.all_decls = []    # ordered list of every declaration (for printing)

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def declare(self, name, sym_type, lineno):
        """Add name to the current (innermost) scope.
        Returns False if the name is already declared in this exact scope."""
        level = len(self.scopes) - 1
        if name in self.scopes[-1]:
            return False
        entry = {'type': sym_type, 'scope': level, 'line': lineno}
        self.scopes[-1][name] = entry
        self.all_decls.append({'name': name, **entry})
        return True

    def lookup(self, name):
        """Search from innermost to outermost scope."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def print_table(self):
        name_width = max([len('Name')] + [len(e['name']) for e in self.all_decls]) + 2
        type_width = max([len('Type')] + [len(e['type']) for e in self.all_decls]) + 2
        header = f"{'Name':<{name_width}} {'Type':<{type_width}} {'Scope':<8} {'Line'}"
        print(header)
        print('-' * len(header))
        for e in self.all_decls:
            print(f"  {e['name']:<{name_width - 2}} {e['type']:<{type_width}} {e['scope']:<8} {e['line']}")


# ---------------------------------------------------------------------------
# Semantic analyser — visitor pattern
# ---------------------------------------------------------------------------
class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors = []
        self.functions = {}
        self.current_function = None

    def error(self, msg, lineno):
        self.errors.append(f"Line {lineno}: {msg}")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def analyze(self, node):
        self.visit(node)
        return self.errors

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------
    def visit(self, node):
        if node is None:
            return None
        method = 'visit_' + type(node).__name__
        return getattr(self, method, self._noop)(node)

    def _noop(self, node):
        return None

    # ------------------------------------------------------------------
    # Visitors — each expression visitor returns its type string
    # ------------------------------------------------------------------
    def visit_Program(self, node):
        for stmt in node.stmts:
            if isinstance(stmt, FunctionDef):
                signature = {
                    'return_type': stmt.return_type,
                    'params': [param.param_type for param in stmt.params],
                }
                self.functions[stmt.name] = signature
                fn_type = f"{stmt.return_type}({', '.join(signature['params'])})"
                if not self.symbol_table.declare(stmt.name, fn_type, stmt.lineno):
                    self.error(
                        f"Function '{stmt.name}' already declared in this scope",
                        stmt.lineno
                    )

        for stmt in node.stmts:
            self.visit(stmt)

    def visit_FunctionDef(self, node):
        previous_function = self.current_function
        self.current_function = node
        self.symbol_table.enter_scope()

        for param in node.params:
            self.visit(param)

        self.visit(node.body)
        self.symbol_table.exit_scope()
        self.current_function = previous_function

    def visit_Param(self, node):
        if not self.symbol_table.declare(node.name, node.param_type, node.lineno):
            self.error(
                f"Parameter '{node.name}' already declared in this function",
                node.lineno
            )

    def visit_VarDecl(self, node):
        init_type = None
        if node.init is not None:
            init_type = self.visit(node.init)

        if init_type is not None and node.var_type in ('int', 'char') and init_type in ('float', 'double'):
            self.error(
                f"Cannot assign {init_type} expression to {node.var_type} variable '{node.name}'",
                node.lineno
            )

        if not self.symbol_table.declare(node.name, node.var_type, node.lineno):
            self.error(
                f"Variable '{node.name}' already declared in this scope",
                node.lineno
            )

    def visit_VarDeclList(self, node):
        for decl in node.decls:
            self.visit(decl)

    def visit_ArrayDecl(self, node):
        if node.size <= 0:
            self.error(
                f"Array '{node.name}' size must be a positive integer",
                node.lineno
            )

        array_type = f'{node.var_type}[]'
        if not self.symbol_table.declare(node.name, array_type, node.lineno):
            self.error(
                f"Variable '{node.name}' already declared in this scope",
                node.lineno
            )

    def visit_Assign(self, node):
        val_type = self.visit(node.value)

        if isinstance(node.target, Identifier):
            sym = self.symbol_table.lookup(node.target.name)
            if sym is None:
                inferred_type = val_type or 'int'
                self.symbol_table.declare(node.target.name, inferred_type, node.lineno)
            else:
                if sym['type'].endswith('[]'):
                    self.error(
                        f"Array '{node.target.name}' used without index in assignment",
                        node.lineno
                    )
                elif sym['type'] in ('int', 'char') and val_type in ('float', 'double'):
                    self.error(
                        f"Cannot assign {val_type} to {sym['type']} variable '{node.target.name}'",
                        node.lineno
                    )

        elif isinstance(node.target, ArrayAccess):
            sym = self.symbol_table.lookup(node.target.name)
            if sym is None:
                self.error(f"Undeclared array '{node.target.name}'", node.lineno)
            elif not sym['type'].endswith('[]'):
                self.error(f"'{node.target.name}' is not an array", node.lineno)
            else:
                elem_type = sym['type'].replace('[]', '')
                if elem_type in ('int', 'char') and val_type in ('float', 'double'):
                    self.error(
                        f"Cannot assign {val_type} to {elem_type} array '{node.target.name}'",
                        node.lineno
                    )

            idx_type = self.visit(node.target.index)
            if idx_type is not None and idx_type != 'int':
                self.error(
                    f"Array index must be int, got '{idx_type}'",
                    node.lineno
                )

    def visit_BinOp(self, node):
        left_type  = self.visit(node.left)
        right_type = self.visit(node.right)

        # Relational operators produce an int (boolean) result
        if node.op in ('<', '>', '<=', '>=', '==', '!=', '&&', '||'):
            return 'int'

        # Arithmetic: float wins over int
        if 'double' in (left_type, right_type):
            return 'double'
        if 'float' in (left_type, right_type):
            return 'float'
        return 'int'

    def visit_UnaryMinus(self, node):
        return self.visit(node.operand)

    def visit_UnaryOp(self, node):
        operand_type = self.visit(node.operand)
        if node.op == '!':
            return 'int'
        if node.op == '&':
            return f'{operand_type}*'
        return operand_type

    def visit_PostfixOp(self, node):
        return self.visit(node.target)

    def visit_IntLit(self, node):
        return 'int'

    def visit_FloatLit(self, node):
        return 'float'

    def visit_StringLit(self, node):
        return 'char[]'

    def visit_CharLit(self, node):
        return 'char'

    def visit_Identifier(self, node):
        sym = self.symbol_table.lookup(node.name)
        if sym is None:
            self.error(f"Undeclared variable '{node.name}'", node.lineno)
            return 'int'   # default prevents cascading errors
        if sym['type'].endswith('[]'):
            self.error(f"Array '{node.name}' used without index", node.lineno)
            return sym['type'].replace('[]', '')
        return sym['type']

    def visit_ArrayAccess(self, node):
        sym = self.symbol_table.lookup(node.name)
        if sym is None:
            self.error(f"Undeclared variable '{node.name}'", node.lineno)
            return 'int'
        if not sym['type'].endswith('[]'):
            self.error(f"'{node.name}' is not an array", node.lineno)
            return 'int'

        idx_type = self.visit(node.index)
        if idx_type is not None and idx_type != 'int':
            self.error(
                f"Array index must be int, got '{idx_type}'",
                node.lineno
            )
        return sym['type'].replace('[]', '')

    def visit_If(self, node):
        self.visit(node.condition)
        self.visit(node.then_body)
        if node.else_body is not None:
            self.visit(node.else_body)

    def visit_While(self, node):
        self.visit(node.condition)
        self.visit(node.body)

    def visit_For(self, node):
        # The for header gets its own scope so the init variable (e.g. int j)
        # is scoped to the loop and not visible after it.
        self.symbol_table.enter_scope()
        if node.init is not None:
            self.visit(node.init)
        if node.condition is not None:
            self.visit(node.condition)
        if node.update is not None:
            self.visit(node.update)
        self.visit(node.body)
        self.symbol_table.exit_scope()

    def visit_Print(self, node):
        self.visit(node.expr)

    def visit_Return(self, node):
        expr_type = self.visit(node.expr) if node.expr is not None else 'void'

        if self.current_function is None:
            self.error("return statement outside a function", node.lineno)
            return

        return_type = self.current_function.return_type
        if return_type == 'void' and node.expr is not None:
            self.error(
                f"Void function '{self.current_function.name}' cannot return a value",
                node.lineno
            )
        elif return_type != 'void' and node.expr is None:
            self.error(
                f"Function '{self.current_function.name}' must return a value",
                node.lineno
            )
        elif return_type in ('int', 'char') and expr_type in ('float', 'double'):
            self.error(
                f"Cannot return {expr_type} from {return_type} function '{self.current_function.name}'",
                node.lineno
            )

    def visit_ExprStmt(self, node):
        self.visit(node.expr)

    def visit_FunctionCall(self, node):
        signature = self.functions.get(node.name)
        arg_types = [self.visit(arg) for arg in node.args]

        if signature is None and node.name in ('printf', 'scanf'):
            return 'int'

        if signature is None:
            self.error(f"Call to undeclared function '{node.name}'", node.lineno)
            return 'int'

        expected = signature['params']
        if len(arg_types) != len(expected):
            self.error(
                f"Function '{node.name}' expects {len(expected)} argument(s), got {len(arg_types)}",
                node.lineno
            )
        else:
            for index, (actual, formal) in enumerate(zip(arg_types, expected), 1):
                if formal in ('int', 'char') and actual in ('float', 'double'):
                    self.error(
                        f"Argument {index} of '{node.name}' expects {formal}, got {actual}",
                        node.lineno
                    )

        return signature['return_type']

    def visit_Block(self, node):
        self.symbol_table.enter_scope()
        for stmt in node.stmts:
            self.visit(stmt)
        self.symbol_table.exit_scope()
