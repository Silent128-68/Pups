import re
import sys
from typing import List, Dict, NamedTuple

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

def lex(line_text: str, line_num: int, id_table: Dict[str, int], const_table: Dict[str, int]) -> List[Lexeme]:
    lexemes = []
    next_id = len(id_table) + 1
    next_const = len(const_table) + 1

    for mo in token_regex.finditer(line_text):
        kind = mo.lastgroup
        val = mo.group(0)
        col = mo.start() + 1

        if kind == 'ID_OR_NUM':
            if val[0].isdigit():
                if val.isdigit():
                    lexemes.append(Lexeme(val, 'CONSTANT', 'constant', line_num, col))
                    if val not in const_table:
                        const_table[val] = next_const
                        next_const += 1
                else:
                    raise ValueError(f"Строка {line_num}, поз. {col}: Недопустимый идентификатор: '{val}'")
            elif val[0].isalpha():
                low = val.lower()
                if low in KEYWORDS:
                    lexemes.append(Lexeme(val, KEYWORDS[low], 'keyword', line_num, col))
                else:
                    lexemes.append(Lexeme(val, 'IDENTIFIER', 'identifier', line_num, col))
                    if low not in id_table:
                        id_table[low] = next_id
                        next_id += 1
        
        elif kind == 'OP':
            op_type, op_cat = 'UNKNOWN_OP', 'operation'
            if val == ';': op_type, op_cat = 'SEMICOLON', 'symbol'
            elif val in ('+', '-', '*', '/'): op_type, op_cat = 'ARITHMETIC', 'operation'
            elif val in ('<=', '>=', '==', '<>', '<', '>'): op_type, op_cat = 'COMPARISON', 'operation'
            elif val == '=': op_type, op_cat = 'ASSIGNMENT', 'operation'
            elif val == '<<': op_type, op_cat = 'IO_OP', 'operation'
            elif val in ('(', ')'): op_type, op_cat = 'PAREN', 'symbol'
            
            lexemes.append(Lexeme(val, op_type, op_cat, line_num, col))
            
        elif kind == 'SKIP': continue
        elif kind == 'MISMATCH':
            raise ValueError(f"Строка {line_num}, поз. {col}: Недопустимый символ: {val!r}")

    return lexemes

class TreeNode:
    def __init__(self, name: str, value: str = ""):
        self.name = name
        self.value = value
        self.children = []

    def add(self, node):
        if isinstance(node, TreeNode): self.children.append(node)
        elif node is not None: self.children.append(TreeNode(str(node)))

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
        raise SyntaxError(f"Ошибка синтаксиса [стр {self.curr.line}, поз {self.curr.col}]: {msg}. Найдено: '{self.curr.value}'")

    def eat(self, expected_type: str, expected_value: str = None):
        if self.curr.type == expected_type:
            if expected_value and self.curr.value.lower() != expected_value.lower():
                 self.error(f"Ожидалось '{expected_value}'")
            val = self.curr.value
            self.advance()
            return val
        else:
            self.error(f"Ожидался тип '{expected_type}'")

    # <Program> -> do until <LogExpr> <Statements> loop
    def parse_program(self) -> TreeNode:
        node = TreeNode("Program")
        node.add(TreeNode("Keyword", self.eat('DO')))
        node.add(TreeNode("Keyword", self.eat('UNTIL')))
        node.add(self.parse_log_expr())    # Условие
        node.add(self.parse_statements())  # Тело цикла
        node.add(TreeNode("Keyword", self.eat('LOOP')))
        if self.curr.type != 'EOF': self.error("Обнаружен лишний код после конца программы")
        return node

    # <Statements> -> <Statement> { <Statement> }
    def parse_statements(self) -> TreeNode:
        node = TreeNode("Statements")
        while self.curr.type not in ('LOOP', 'EOF'):
            node.add(self.parse_statement())
        return node

    # <Statement> -> Input | Output | Assignment
    def parse_statement(self) -> TreeNode:
        if self.curr.type == 'INPUT':
            n = TreeNode("InputStatement"); self.eat('INPUT'); self.eat('IO_OP')
            n.add(TreeNode("Identifier", self.eat('IDENTIFIER'))); self.eat('SEMICOLON')
            return n
        elif self.curr.type == 'OUTPUT':
            n = TreeNode("OutputStatement"); self.eat('OUTPUT'); self.eat('IO_OP')
            n.add(self.parse_arith_expr()); self.eat('SEMICOLON')
            return n
        elif self.curr.type == 'IDENTIFIER':
            n = TreeNode("Assignment"); n.add(TreeNode("Target", self.eat('IDENTIFIER')))
            self.eat('ASSIGNMENT'); n.add(self.parse_arith_expr()); self.eat('SEMICOLON')
            return n
        self.error("Ожидался оператор (input, output или присваивание)")

    # <LogExpr>
    def parse_log_expr(self) -> TreeNode:
        node = self.parse_log_term()
        while self.curr.type == 'LOGICAL_OP' and self.curr.value.lower() == 'or':
            op_val = self.eat('LOGICAL_OP')
            new_node = TreeNode("LogicalOr"); new_node.add(node); new_node.add(self.parse_log_term())
            node = new_node
        return node

    def parse_log_term(self) -> TreeNode:
        node = self.parse_log_factor()
        while self.curr.type == 'LOGICAL_OP' and self.curr.value.lower() == 'and':
            op_val = self.eat('LOGICAL_OP')
            new_node = TreeNode("LogicalAnd"); new_node.add(node); new_node.add(self.parse_log_factor())
            node = new_node
        return node

    def parse_log_factor(self) -> TreeNode:
        if self.curr.type == 'LOGICAL_NOT':
            n = TreeNode("LogicalNot"); self.eat('LOGICAL_NOT'); n.add(self.parse_log_factor()); return n
        return self.parse_comparison()

    def parse_comparison(self) -> TreeNode:
        left = self.parse_arith_expr()
        if self.curr.type == 'COMPARISON':
            op = self.eat('COMPARISON')
            node = TreeNode("Comparison", op); node.add(left); node.add(self.parse_arith_expr())
            return node
        return left

    # <ArithExpr>
    def parse_arith_expr(self) -> TreeNode:
        node = self.parse_term()
        while self.curr.type == 'ARITHMETIC' and self.curr.value in ('+', '-'):
            op = self.eat('ARITHMETIC')
            new_node = TreeNode("ArithOp", op); new_node.add(node); new_node.add(self.parse_term())
            node = new_node
        return node

    def parse_term(self) -> TreeNode:
        node = self.parse_factor()
        while self.curr.type == 'ARITHMETIC' and self.curr.value in ('*', '/'):
            op = self.eat('ARITHMETIC')
            new_node = TreeNode("ArithOp", op); new_node.add(node); new_node.add(self.parse_factor())
            node = new_node
        return node

    def parse_factor(self) -> TreeNode:
        if self.curr.type == 'IDENTIFIER': return TreeNode("Var", self.eat('IDENTIFIER'))
        elif self.curr.type == 'CONSTANT': return TreeNode("Const", self.eat('CONSTANT'))
        elif self.curr.type == 'PAREN' and self.curr.value == '(':
            self.eat('PAREN', '('); n = self.parse_arith_expr(); self.eat('PAREN', ')'); return n
        self.error("Ожидался идентификатор, число или '('")

def main():
    try:
        with open("FL_1lab_input.txt", "r", encoding="utf-8") as f: text = f.read()
    except FileNotFoundError:
        text = "do until (x + y) < 10\n  input << a;\n  b = a * 2;\n  output << b;\nloop"
        print("Файл не найден, используется тест.")

    print(f"Код:\n{text}\n" + "-"*50)
    all_lexemes = []
    id_table, const_table = {}, {}

    try:
        for i, line in enumerate(text.splitlines(), 1):
            all_lexemes.extend(lex(line, i, id_table, const_table))
        
        parser = RecursiveDescentParser(all_lexemes)
        print(parser.parse_program())
        print("\nАнализ завершен.")
    except Exception as e:
        print(f"\nОшибка: {e}")

if __name__ == "__main__":
    main()
