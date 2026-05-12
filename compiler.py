"""
compiler.py - CLI entry point and shared pipeline for the Mini-C compiler.

Usage:
    python compiler.py [source_file]   (defaults to test_program.mc)

Stages executed:
    1. Lexer        - tokenise the source
    2. Parser       - build the AST
    3. Semantic     - symbol table + type checking
    4. TAC gen      - emit three-address code

Output:
    - Token stream  (stage 1)
    - Parse tree / AST  (stage 2, also written to parse_tree.txt)
    - Symbol table  (after stage 3)
    - Numbered TAC  (stage 4, also written to tac_output.txt)
"""

import io
import sys
from contextlib import redirect_stdout

from lexer import lexer
from parser import parser
from semantic import SemanticAnalyzer
from tac_gen import TACGenerator


def divider(title):
    width = 62
    print()
    print('=' * width)
    print(f'  {title}')
    print('=' * width)


def is_ast_node(value):
    return hasattr(value, '__dict__') and value.__class__.__module__ == 'ast_nodes'


def node_parts(node):
    scalar_parts = []
    children = []

    for name, value in node.__dict__.items():
        if is_ast_node(value):
            children.append((name, value))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if is_ast_node(item):
                    children.append((f'{name}[{i}]', item))
                else:
                    scalar_parts.append(f'{name}[{i}]={item!r}')
        else:
            scalar_parts.append(f'{name}={value!r}')

    summary = type(node).__name__
    if scalar_parts:
        summary += '(' + ', '.join(scalar_parts) + ')'
    return summary, children


def build_tree_lines(node):
    if node is None:
        return ['<empty>']

    root_summary, root_children = node_parts(node)
    lines = [root_summary]

    def add_child(label, child, prefix, is_last):
        branch = '`-- ' if is_last else '|-- '
        summary, children = node_parts(child)
        lines.append(f'{prefix}{branch}{label}: {summary}')

        child_prefix = prefix + ('    ' if is_last else '|   ')
        for i, (child_label, grandchild) in enumerate(children):
            add_child(child_label, grandchild, child_prefix, i == len(children) - 1)

    for i, (label, child) in enumerate(root_children):
        add_child(label, child, '', i == len(root_children) - 1)

    return lines


def print_parse_tree(ast):
    lines = build_tree_lines(ast)
    for line in lines:
        print(f'  {line}')
    return lines


def write_lines(filename, lines):
    with open(filename, 'w') as f:
        for line in lines:
            f.write(line + '\n')


def capture_output(func, *args, **kwargs):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)
    return result, buffer.getvalue().splitlines()


def symbol_table_lines(symbol_table):
    _, lines = capture_output(symbol_table.print_table)
    return lines


def tac_lines(generator):
    return [f'  {i:3}: {instr}' for i, instr in enumerate(generator.instructions, 1)]


def compile_source(source, write_outputs=True):
    sections = {}

    # Stage 1 - Lexer
    lexer.lineno = 1
    lexer.input(source)
    tokens_found, lexer_messages = capture_output(lambda: list(lexer))
    token_lines = lexer_messages[:]
    for tok in tokens_found:
        token_lines.append(f'  {tok.type:<12} {repr(tok.value):<18} line {tok.lineno}')
    token_lines.append('')
    token_lines.append(f'  {len(tokens_found)} tokens produced.')
    sections['lexer'] = token_lines

    # Stage 2 - Parser
    lexer.lineno = 1
    ast, parser_messages = capture_output(parser.parse, source, lexer=lexer)
    parser_lines = parser_messages[:]
    if ast is None:
        parser_lines.append('  Parse failed - aborting.')
        sections['parser'] = parser_lines
        return {'ok': False, 'sections': sections, 'errors': parser_lines}

    parser_lines.append('  AST built successfully.')
    sections['parser'] = parser_lines

    parse_tree_lines = build_tree_lines(ast)
    sections['parse_tree'] = parse_tree_lines
    if write_outputs:
        write_lines('parse_tree.txt', parse_tree_lines)

    # Stage 3 - Semantic analysis
    analyzer = SemanticAnalyzer()
    errors = analyzer.analyze(ast)

    if errors:
        semantic_lines = [f'  {len(errors)} semantic error(s) found:', '']
        for err in errors:
            semantic_lines.append(f'    {err}')
        semantic_lines.append('')
        semantic_lines.append('  Halting - fix errors before TAC generation.')
        sections['semantic'] = semantic_lines
        return {'ok': False, 'sections': sections, 'errors': errors, 'ast': ast}

    sections['semantic'] = ['  No semantic errors.']
    sections['symbol_table'] = symbol_table_lines(analyzer.symbol_table)

    # Stage 4 - TAC generation
    gen = TACGenerator()
    gen.generate(ast)
    sections['tac'] = tac_lines(gen)
    if write_outputs:
        gen.write_to_file('tac_output.txt')

    return {
        'ok': True,
        'sections': sections,
        'tokens': tokens_found,
        'ast': ast,
        'symbol_table': analyzer.symbol_table,
        'tac_generator': gen,
    }


def print_section(title, lines):
    divider(title)
    for line in lines:
        print(line)


def run(source_file):
    try:
        with open(source_file, 'r') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: cannot open '{source_file}'")
        sys.exit(1)

    result = compile_source(source, write_outputs=True)
    sections = result['sections']

    print_section('STAGE 1: LEXER', sections.get('lexer', []))
    print_section('STAGE 2: PARSER  (building AST)', sections.get('parser', []))

    if 'parse_tree' in sections:
        print_section('PARSE TREE / AST', [f'  {line}' for line in sections['parse_tree']])
        print()
        print('  Parse tree written to parse_tree.txt')

    if 'semantic' in sections:
        print_section('STAGE 3: SEMANTIC ANALYSIS', sections['semantic'])

    if result['ok']:
        print()
        print_section('SYMBOL TABLE', sections.get('symbol_table', []))
        print_section('STAGE 4: THREE-ADDRESS CODE', sections.get('tac', []))
        print(f"\n  {len(result['tac_generator'].instructions)} instructions written to tac_output.txt")
    else:
        sys.exit(1)


if __name__ == '__main__':
    source_file = sys.argv[1] if len(sys.argv) > 1 else 'test_program.mc'
    run(source_file)
