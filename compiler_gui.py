import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from compiler import compile_source, node_parts


class MiniCCompilerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Mini-C Compiler')
        self.geometry('1200x760')
        self.minsize(900, 600)
        self.source_path = None

        self._build_ui()
        self.load_file('test_program.mc', show_error=False)

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
        parse_frame.rowconfigure(0, weight=1)
        parse_frame.columnconfigure(0, weight=1)
        parse_frame.columnconfigure(1, weight=0)

        self.parse_tree = ttk.Treeview(parse_frame, show='tree')
        tree_scroll_y = ttk.Scrollbar(parse_frame, orient='vertical', command=self.parse_tree.yview)
        tree_scroll_x = ttk.Scrollbar(parse_frame, orient='horizontal', command=self.parse_tree.xview)
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
            self.tabs.select(self.parse_tree.master)
        else:
            self.status_var.set('Compilation stopped with errors.')
            if result.get('ast') is not None:
                self.tabs.select(self.parse_tree.master)
            else:
                self.tabs.select(self.output_widgets['semantic'].master)

    def build_all_output(self, sections):
        titles = (
            ('STAGE 1: LEXER', 'lexer'),
            ('STAGE 2: PARSER', 'parser'),
            ('PARSE TREE / AST', 'parse_tree'),
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
            self.parse_tree.insert('', 'end', text='No parse tree available')
            return

        def add_node(parent, label, node, open_node=True):
            summary, children = node_parts(node)
            text = summary if label is None else f'{label}: {summary}'
            item_id = self.parse_tree.insert(parent, 'end', text=text, open=open_node)
            for child_label, child in children:
                add_node(item_id, child_label, child, open_node=True)

        add_node('', None, ast)

    def clear_outputs(self):
        for key in self.output_widgets:
            self.set_output(key, [])
        self.populate_parse_tree(None)
        self.status_var.set('Output cleared')


if __name__ == '__main__':
    app = MiniCCompilerApp()
    app.mainloop()
