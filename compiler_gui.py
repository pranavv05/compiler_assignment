import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from compiler import compile_source, node_parts


class MiniCCompilerApp(tk.Tk):
    def __init__(self, initial_path='test_program.mc'):
        super().__init__()
        self.title('Mini-C Compiler')
        self.geometry('1200x760')
        self.minsize(900, 600)
        self.source_path = None

        self._build_ui()
        self.load_file(initial_path, show_error=False)

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.grid(row=0, column=0, sticky='ew')
        toolbar.columnconfigure(4, weight=1)

        ttk.Button(toolbar, text='Open', command=self.open_file).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(toolbar, text='Run Compiler', command=self.run_compiler).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(toolbar, text='Load Sample', command=lambda: self.load_file('test_program.mc')).grid(
            row=0, column=2, padx=(0, 6)
        )
        ttk.Button(toolbar, text='Clear Output', command=self.clear_outputs).grid(row=0, column=3)

        self.status_var = tk.StringVar(value='Ready')
        ttk.Label(toolbar, textvariable=self.status_var, anchor='e').grid(row=0, column=4, sticky='e')

        pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pane.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 10))

        source_frame = ttk.Frame(pane)
        source_frame.rowconfigure(1, weight=1)
        source_frame.columnconfigure(0, weight=1)
        pane.add(source_frame, weight=1)

        ttk.Label(source_frame, text='Source Code').grid(row=0, column=0, sticky='w', pady=(0, 6))
        self.source_text = ScrolledText(source_frame, wrap='none', font=('Consolas', 11), undo=True)
        self.source_text.grid(row=1, column=0, sticky='nsew')

        output_frame = ttk.Frame(pane)
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        pane.add(output_frame, weight=2)

        self.tabs = ttk.Notebook(output_frame)
        self.tabs.grid(row=0, column=0, sticky='nsew')

        self.output_widgets = {}
        for key, title in (
            ('lexer', 'Tokens'),
            ('parser', 'Parser'),
            ('semantic', 'Semantic'),
            ('symbol_table', 'Symbol Table'),
            ('tac', 'TAC'),
            ('all', 'All Output'),
        ):
            frame = ttk.Frame(self.tabs)
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            text = ScrolledText(frame, wrap='none', font=('Consolas', 10), state='disabled')
            text.grid(row=0, column=0, sticky='nsew')
            self.tabs.add(frame, text=title)
            self.output_widgets[key] = text

        parse_frame = ttk.Frame(self.tabs)
        self.parse_tab = parse_frame
        parse_frame.rowconfigure(1, weight=1)
        parse_frame.columnconfigure(0, weight=1)

        parse_header = ttk.Frame(parse_frame, padding=(8, 6))
        parse_header.grid(row=0, column=0, sticky='ew')
        parse_header.columnconfigure(0, weight=1)

        ttk.Label(parse_header, text='Visual Parse Tree', font=('Segoe UI', 11, 'bold')).grid(
            row=0, column=0, sticky='w'
        )
        self.parse_status_var = tk.StringVar(value='No parse tree available')
        ttk.Label(parse_header, textvariable=self.parse_status_var, anchor='e').grid(
            row=0, column=1, sticky='e'
        )

        tree_frame = ttk.Frame(parse_frame)
        tree_frame.grid(row=1, column=0, sticky='nsew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        columns = ('node_type', 'properties')
        self.parse_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='tree headings',
            selectmode='browse',
        )
        self.parse_tree.heading('#0', text='Field / Child')
        self.parse_tree.heading('node_type', text='Node Type')
        self.parse_tree.heading('properties', text='Properties')
        self.parse_tree.column('#0', width=230, minwidth=160, stretch=True)
        self.parse_tree.column('node_type', width=150, minwidth=110, stretch=False)
        self.parse_tree.column('properties', width=520, minwidth=260, stretch=True)

        self.parse_tree.tag_configure('root', font=('Segoe UI', 10, 'bold'))
        self.parse_tree.tag_configure('statement', foreground='#174ea6')
        self.parse_tree.tag_configure('expression', foreground='#0b8043')
        self.parse_tree.tag_configure('literal', foreground='#8e24aa')
        self.parse_tree.tag_configure('control', foreground='#b06000')

        tree_scroll_y = ttk.Scrollbar(tree_frame, orient='vertical', command=self.parse_tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.parse_tree.xview)
        self.parse_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        self.parse_tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll_y.grid(row=0, column=1, sticky='ns')
        tree_scroll_x.grid(row=1, column=0, sticky='ew')
        self.tabs.insert(2, parse_frame, text='Parse Tree')

    def open_file(self):
        path = filedialog.askopenfilename(
            title='Open Mini-C source file',
            filetypes=(('Mini-C files', '*.mc'), ('Text files', '*.txt'), ('All files', '*.*')),
        )
        if path:
            self.load_file(path)

    def load_file(self, path, show_error=True):
        try:
            with open(path, 'r') as f:
                source = f.read()
        except OSError as exc:
            if show_error:
                messagebox.showerror('Open failed', str(exc))
            return

        self.source_path = path
        self.source_text.delete('1.0', tk.END)
        self.source_text.insert('1.0', source)
        self.status_var.set(f'Loaded {os.path.basename(path)}')

    def run_compiler(self):
        source = self.source_text.get('1.0', tk.END)
        result = compile_source(source, write_outputs=True)
        sections = result['sections']

        self.set_output('lexer', sections.get('lexer', []))
        self.set_output('parser', sections.get('parser', []))
        self.populate_parse_tree(result.get('ast'))
        self.set_output('semantic', sections.get('semantic', []))
        self.set_output('symbol_table', sections.get('symbol_table', []))
        self.set_output('tac', sections.get('tac', []))
        self.set_output('all', self.build_all_output(sections))

        if result['ok']:
            count = len(result['tac_generator'].instructions)
            self.status_var.set(f'Compiled successfully. {count} TAC instructions generated.')
            self.tabs.select(self.parse_tab)
        else:
            self.status_var.set('Compilation stopped with errors.')
            if result.get('ast') is not None:
                self.tabs.select(self.parse_tab)
            elif sections.get('parser'):
                self.tabs.select(self.output_widgets['parser'].master)
            elif sections.get('lexer'):
                self.tabs.select(self.output_widgets['lexer'].master)
            else:
                self.tabs.select(self.output_widgets['semantic'].master)

    def build_all_output(self, sections):
        titles = (
            ('STAGE 1: LEXER', 'lexer'),
            ('STAGE 2: PARSER', 'parser'),
            ('STAGE 3: SEMANTIC ANALYSIS', 'semantic'),
            ('SYMBOL TABLE', 'symbol_table'),
            ('STAGE 4: THREE-ADDRESS CODE', 'tac'),
        )
        lines = []
        for title, key in titles:
            if key not in sections:
                continue
            if lines:
                lines.append('')
            lines.append('=' * 62)
            lines.append(f'  {title}')
            lines.append('=' * 62)
            lines.extend(sections[key])
        return lines

    def set_output(self, key, lines):
        text = self.output_widgets[key]
        text.configure(state='normal')
        text.delete('1.0', tk.END)
        text.insert('1.0', '\n'.join(lines))
        text.configure(state='disabled')

    def populate_parse_tree(self, ast):
        self.parse_tree.delete(*self.parse_tree.get_children())
        if ast is None:
            self.parse_status_var.set('No parse tree available')
            self.parse_tree.insert(
                '',
                'end',
                text='Compile valid source to generate a visual tree',
                values=('', ''),
                tags=('root',),
            )
            return

        self.parse_status_var.set('Structured AST view')

        def node_tag(node_or_name):
            name = node_or_name if isinstance(node_or_name, str) else type(node_or_name).__name__
            if name == 'Program':
                return 'root'
            if name in (
                'FunctionDef', 'If', 'While', 'For', 'Block', 'Return', 'Print',
                'Assign', 'VarDecl', 'VarDeclList', 'ArrayDecl',
            ):
                return 'statement'
            if name in (
                'BinOp', 'UnaryMinus', 'UnaryOp', 'PostfixOp', 'Identifier',
                'ArrayAccess', 'FunctionCall', 'ExprStmt',
            ):
                return 'expression'
            if name in ('IntLit', 'FloatLit', 'StringLit', 'CharLit'):
                return 'literal'
            return 'control'

        def insert_row(parent, label, node_type, properties='', open_node=True, tag=None):
            return self.parse_tree.insert(
                parent,
                'end',
                text=label,
                values=(node_type, properties),
                open=open_node,
                tags=(tag or node_tag(node_type),),
            )

        def insert_group(parent, label):
            return insert_row(parent, label, 'Group', '', True, 'control')

        def add_expr(parent, label, node):
            name = type(node).__name__

            if name == 'BinOp':
                item = insert_row(parent, label, 'Binary Expression', f'operator {node.op}', True, 'expression')
                add_expr(item, 'Left operand', node.left)
                add_expr(item, 'Right operand', node.right)
                return item

            if name == 'UnaryMinus':
                item = insert_row(parent, label, 'Unary Expression', 'operator -', True, 'expression')
                add_expr(item, 'Operand', node.operand)
                return item

            if name == 'UnaryOp':
                item = insert_row(parent, label, 'Unary Expression', f'operator {node.op}', True, 'expression')
                add_expr(item, 'Operand', node.operand)
                return item

            if name == 'PostfixOp':
                item = insert_row(parent, label, 'Postfix Expression', f'operator {node.op}', True, 'expression')
                add_expr(item, 'Target', node.target)
                return item

            if name == 'Identifier':
                return insert_row(parent, label, 'Identifier', f'name {node.name}', False, 'expression')

            if name == 'ArrayAccess':
                item = insert_row(parent, label, 'Array Access', f'name {node.name}', True, 'expression')
                add_expr(item, 'Index', node.index)
                return item

            if name == 'FunctionCall':
                item = insert_row(parent, label, 'Function Call', f'name {node.name}', True, 'expression')
                args = insert_group(item, 'Arguments')
                if node.args:
                    for index, arg in enumerate(node.args, 1):
                        add_expr(args, f'Argument {index}', arg)
                else:
                    insert_row(args, 'No arguments', 'Empty', '', False, 'control')
                return item

            if name == 'IntLit':
                return insert_row(parent, label, 'Integer Literal', f'value {node.value}', False, 'literal')

            if name == 'FloatLit':
                return insert_row(parent, label, 'Float Literal', f'value {node.value}', False, 'literal')

            if name == 'StringLit':
                return insert_row(parent, label, 'String Literal', f'value "{node.value}"', False, 'literal')

            if name == 'CharLit':
                return insert_row(parent, label, 'Character Literal', f"value '{node.value}'", False, 'literal')

            if name == 'ExprStmt':
                item = insert_row(parent, label, 'Expression Statement', '', True, 'expression')
                add_expr(item, 'Expression', node.expr)
                return item

            return add_stmt(parent, label, node)

        def add_stmt(parent, label, node):
            name = type(node).__name__

            if name == 'FunctionDef':
                item = insert_row(
                    parent,
                    label,
                    'Function Definition',
                    f'name {node.name}, returns {node.return_type}, line {node.lineno}',
                    True,
                    'statement',
                )
                params = insert_group(item, 'Parameters')
                if node.params:
                    for index, param in enumerate(node.params, 1):
                        insert_row(
                            params,
                            f'Parameter {index}',
                            'Parameter',
                            f'{param.param_type} {param.name}',
                            False,
                            'control',
                        )
                else:
                    insert_row(params, 'No parameters', 'Empty', '', False, 'control')
                add_stmt(item, 'Body', node.body)
                return item

            if name == 'Block':
                item = insert_row(parent, label, 'Block', f'{len(node.stmts)} statement(s)', True, 'statement')
                for index, stmt in enumerate(node.stmts, 1):
                    add_stmt(item, f'Statement {index}', stmt)
                return item

            if name == 'VarDecl':
                item = insert_row(
                    parent,
                    label,
                    'Variable Declaration',
                    f'{node.var_type} {node.name}, line {node.lineno}',
                    True,
                    'statement',
                )
                if node.init is not None:
                    add_expr(item, 'Initial value', node.init)
                return item

            if name == 'VarDeclList':
                item = insert_row(parent, label, 'Declaration List', f'{len(node.decls)} variable(s)', True, 'statement')
                for index, decl in enumerate(node.decls, 1):
                    add_stmt(item, f'Declaration {index}', decl)
                return item

            if name == 'ArrayDecl':
                return insert_row(
                    parent,
                    label,
                    'Array Declaration',
                    f'{node.var_type} {node.name}[{node.size}], line {node.lineno}',
                    False,
                    'statement',
                )

            if name == 'Assign':
                item = insert_row(parent, label, 'Assignment', f'line {node.lineno}', True, 'statement')
                add_expr(item, 'Target', node.target)
                add_expr(item, 'Value', node.value)
                return item

            if name == 'Return':
                item = insert_row(parent, label, 'Return Statement', f'line {node.lineno}', True, 'statement')
                if node.expr is not None:
                    add_expr(item, 'Return value', node.expr)
                return item

            if name == 'Print':
                item = insert_row(parent, label, 'Print Statement', f'line {node.lineno}', True, 'statement')
                add_expr(item, 'Expression', node.expr)
                return item

            if name == 'If':
                item = insert_row(parent, label, 'If Statement', f'line {node.lineno}', True, 'statement')
                add_expr(item, 'Condition', node.condition)
                add_stmt(item, 'Then branch', node.then_body)
                if node.else_body is not None:
                    add_stmt(item, 'Else branch', node.else_body)
                return item

            if name == 'While':
                item = insert_row(parent, label, 'While Loop', f'line {node.lineno}', True, 'statement')
                add_expr(item, 'Condition', node.condition)
                add_stmt(item, 'Body', node.body)
                return item

            if name == 'For':
                item = insert_row(parent, label, 'For Loop', f'line {node.lineno}', True, 'statement')
                if node.init is not None:
                    add_stmt(item, 'Initialization', node.init)
                if node.condition is not None:
                    add_expr(item, 'Condition', node.condition)
                if node.update is not None:
                    add_stmt(item, 'Update', node.update)
                add_stmt(item, 'Body', node.body)
                return item

            if name == 'ExprStmt':
                return add_expr(parent, label, node)

            return insert_row(parent, label, name, repr(getattr(node, '__dict__', '')), False, node_tag(name))

        root = insert_row('', 'Program', 'Program', f'{len(ast.stmts)} top-level item(s)', True, 'root')
        for index, stmt in enumerate(ast.stmts, 1):
            add_stmt(root, f'Top-level item {index}', stmt)

    def clear_outputs(self):
        for key in self.output_widgets:
            self.set_output(key, [])
        self.populate_parse_tree(None)
        self.status_var.set('Output cleared')


if __name__ == '__main__':
    app = MiniCCompilerApp()
    app.mainloop()
