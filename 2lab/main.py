import re
import sys
from typing import List, Dict, NamedTuple, Optional

class Lexeme(NamedTuple):
    value: str
    type: str
    category: str
    line: int
    col: int

KEYWORDS = {
    'do': 'DO', 'until': 'UNTIL', 'loop': 'LOOP',
    'input': 'INPUT', 'output': 'OUTPUT',
    'and': 'LOGICAL_OP', 'or': 'LOGICAL_OP', 'not': 'LOGICAL_NOT',
}

TOKEN_SPECS = [
    ('ID_OR_NUM', r'[A-Za-z][A-Za-z0-9_]*|\d+[A-Za-z0-9_]*'),
    ('OP',        r'<<|<=|>=|==|<>|[<>=+\-*/;()=]'),
    ('SKIP',      r'[ \t\r]+'), 
    ('MISMATCH',  r'.'),
]

token_regex = re.compile('|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPECS))

def lex(line_text: str, line_num: int, id_table: Dict, const_table: Dict) -> List[Lexeme]:
    lexemes = []
    for mo in token_regex.finditer(line_text):
        kind = mo.lastgroup
        val = mo.group(0)
        col = mo.start() + 1

        if kind == 'ID_OR_NUM':
            if val[0].isdigit():
                if val.isdigit():
                    lexemes.append(Lexeme(val, 'CONSTANT', 'constant', line_num, col))
                else:
                    raise ValueError(f"Lexer Error [{line_num}:{col}]: Invalid ID '{val}'")
            else:
                low = val.lower()
                if low in KEYWORDS:
                    lexemes.append(Lexeme(val, KEYWORDS[low], 'keyword', line_num, col))
                else:
                    lexemes.append(Lexeme(val, 'IDENTIFIER', 'identifier', line_num, col))
        elif kind == 'OP':
            op_type = 'UNKNOWN'
            if val == ';': op_type = 'SEMICOLON'
            elif val in ('+', '-', '*', '/'): op_type = 'ARITHMETIC'
            elif val in ('<=', '>=', '==', '<>', '<', '>'): op_type = 'COMPARISON'
            elif val == '=': op_type = 'ASSIGNMENT'
            elif val == '<<': op_type = 'IO_OP'
            elif val in ('(', ')'): op_type = 'PAREN'
            lexemes.append(Lexeme(val, op_type, 'op', line_num, col))
        elif kind == 'SKIP': continue
        elif kind == 'MISMATCH': raise ValueError(f"Lexer Error: '{val}'")
    return lexemes

class TreeNode:
    def __init__(self, name: str, value: str = ""):
        self.name = name
        self.value = value
        self.children = []

    def add(self, node):
        if node: self.children.append(node)

    def __repr__(self, level=0):
        ret = "  " * level + f"{self.name}" + (f": {self.value}" if self.value else "") + "\n"
        for child in self.children: ret += child.__repr__(level + 1)
        return ret

class RecursiveDescentParser:
    def __init__(self, lexemes: List[Lexeme]):
        self.lexemes = lexemes
        self.pos = 0
        self.curr = lexemes[0] if lexemes else Lexeme("EOF", "EOF", "eof", -1, -1)

    def advance(self):
        self.pos += 1
        if self.pos < len(self.lexemes): self.curr = self.lexemes[self.pos]
        else: self.curr = Lexeme("EOF", "EOF", "eof", -1, -1)

    def error(self, msg):
        raise SyntaxError(f"Syntax Error [{self.curr.line}:{self.curr.col}]: {msg}. Found: '{self.curr.value}'")

    def eat(self, expected_type: str, val: str = None):
        if self.curr.type == expected_type:
            if val and self.curr.value.lower() != val:
                self.error(f"Expected '{val}'")
            res = self.curr.value
            self.advance()
            return res
        self.error(f"Expected type {expected_type}")

    # <Program> -> do until <LogExpr> <Statements> loop
    def parse_program(self):
        node = TreeNode("Program")
        node.add(TreeNode("Keyword", self.eat('DO')))
        node.add(TreeNode("Keyword", self.eat('UNTIL')))
        node.add(self.parse_log_expr())
        node.add(self.parse_statements())
        node.add(TreeNode("Keyword", self.eat('LOOP')))
        if self.curr.type != 'EOF': self.error("Unexpected tokens after end")
        return node

    # <Statements> -> <Statement> <Statements> | epsilon
    def parse_statements(self):
        if self.curr.type == 'LOOP' or self.curr.type == 'EOF':
            return None 
        
        node = TreeNode("Statements")
        node.add(self.parse_statement())
        
        if self.curr.type in ('INPUT', 'OUTPUT', 'IDENTIFIER'):
             node.add(self.parse_statements())
             
        return node

    def parse_statement(self):
        if self.curr.type == 'INPUT':
            n = TreeNode("Input"); self.eat('INPUT'); self.eat('IO_OP')
            n.add(TreeNode("Var", self.eat('IDENTIFIER'))); self.eat('SEMICOLON')
            return n
        elif self.curr.type == 'OUTPUT':
            n = TreeNode("Output"); self.eat('OUTPUT'); self.eat('IO_OP')
            n.add(self.parse_arith_expr()); self.eat('SEMICOLON')
            return n
        elif self.curr.type == 'IDENTIFIER':
            n = TreeNode("Assign"); n.add(TreeNode("Var", self.eat('IDENTIFIER')))
            self.eat('ASSIGNMENT'); n.add(self.parse_arith_expr()); self.eat('SEMICOLON')
            return n
        self.error("Expected Statement")

    def parse_arith_expr(self):
        left = self.parse_term()
        return self.parse_arith_expr_tail(left)

    def parse_arith_expr_tail(self, left_node):
        if self.curr.type == 'ARITHMETIC' and self.curr.value in ('+', '-'):
            op_val = self.eat('ARITHMETIC')
            op_node = TreeNode("Op", op_val)
            
            op_node.add(left_node)
            
            right = self.parse_term()
            op_node.add(right)
            
            return self.parse_arith_expr_tail(op_node)
        
        return left_node

    def parse_term(self):
        left = self.parse_factor()
        return self.parse_term_tail(left)

    def parse_term_tail(self, left_node):
        if self.curr.type == 'ARITHMETIC' and self.curr.value in ('*', '/'):
            op_val = self.eat('ARITHMETIC')
            op_node = TreeNode("Op", op_val)
            op_node.add(left_node)
            right = self.parse_factor()
            op_node.add(right)
            return self.parse_term_tail(op_node)
        return left_node

    def parse_factor(self):
        if self.curr.type == 'IDENTIFIER': return TreeNode("Var", self.eat('IDENTIFIER'))
        if self.curr.type == 'CONSTANT': return TreeNode("Const", self.eat('CONSTANT'))
        if self.curr.value == '(': 
            self.eat('PAREN')
            n = self.parse_arith_expr() 
            self.eat('PAREN')
            return n
        self.error("Invalid Factor")

    def parse_log_expr(self):
        left = self.parse_log_term()
        return self.parse_log_expr_tail(left)

    def parse_log_expr_tail(self, left_node):
        if self.curr.type == 'LOGICAL_OP' and self.curr.value == 'or':
            op_val = self.eat('LOGICAL_OP')
            op_node = TreeNode("Logic", op_val)
            op_node.add(left_node)
            right = self.parse_log_term()
            op_node.add(right)
            return self.parse_log_expr_tail(op_node)
        return left_node

    def parse_log_term(self):
        left = self.parse_log_factor()
        return self.parse_log_term_tail(left)
        
    def parse_log_term_tail(self, left_node):
        if self.curr.type == 'LOGICAL_OP' and self.curr.value == 'and':
            op_val = self.eat('LOGICAL_OP')
            op_node = TreeNode("Logic", op_val)
            op_node.add(left_node)
            right = self.parse_log_factor()
            op_node.add(right)
            return self.parse_log_term_tail(op_node)
        return left_node

    def parse_log_factor(self):
        if self.curr.type == 'LOGICAL_NOT':
            n = TreeNode("Not", self.eat('LOGICAL_NOT'))
            n.add(self.parse_log_factor())
            return n
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_arith_expr()
        if self.curr.type == 'COMPARISON':
            op_val = self.eat('COMPARISON')
            op_node = TreeNode("Cmp", op_val)
            op_node.add(left)
            op_node.add(self.parse_arith_expr())
            return op_node
        return left

def main():
    filename = "FL_1lab_input.txt"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print("Файл не найден. Использую тест.")
        text = "do until x > 10\n x = x + 1; \nloop"

    print(f"Код:\n{text}\n" + "-"*40)
    
    tokens = []
    try:
        for i, line in enumerate(text.splitlines(), 1):
            tokens.extend(lex(line, i, {}, {}))
        
        parser = RecursiveDescentParser(tokens)
        tree = parser.parse_program()
        print("Дерево разбора:")
        print(tree)
        print("Анализ успешен (использована только рекурсия!)")
            
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
