import re
import sys
from enum import Enum
from typing import Union, Optional, List, Dict, NamedTuple, Tuple

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

class Command(Enum):
    JMP = "JMP"; JZ = "JZ"; MOV = "MOV"
    ADD = "ADD"; SUB = "SUB"; MUL = "MUL"; DIV = "DIV"
    CMPL = "CMPL"; CMPG = "CMPG"; CMPE = "CMPE"; CMPNE = "CMPNE"; CMPLE = "CMPLE"; CMPGE = "CMPGE"
    INPUT = "INPUT"; OUTPUT = "OUTPUT"
    AND = "AND"; OR = "OR"; NOT = "NOT" # Добавляем логические команды

class EntryType(Enum):
    COMMAND = "COMMAND"; VARIABLE = "VARIABLE"; CONSTANT = "CONSTANT"; ADDR = "ADDR"

class Entry:
    def __init__(self, etype: EntryType, data: Union[Command, str, int]):
        self.type = etype
        self.data = data
    def __repr__(self):
        if self.type == EntryType.COMMAND: return self.data.value
        return str(self.data)

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
    
    def generate_poliz(self, node: 'TreeNode') -> List[Entry]:
        # 1. Генерация сырого списка с метками
        self.entries = [] 
        self.jmp_patches = [] 
        self._poliz_generator(node)
        
        # 2. Создаем карту меток
        label_map = {}
        clean_idx = 0
        for entry in self.entries:
            if entry.type == EntryType.ADDR and entry.data in ['COND_START', 'BODY_START', 'LOOP_END']:
                label_map[entry.data] = clean_idx
            else:
                clean_idx += 1
        # ----------------------------------------------------
                
        # 3. Создаем финальный список и патчим только аргументы прыжков
        final_entries = []
        patch_dict = {idx: tag for idx, tag in self.jmp_patches}
        
        original_idx = 0
        for entry in self.entries:
            
            # --- Логика патчинга: замена строкового адреса на число ---
            if original_idx in patch_dict:
                target_tag_alias = patch_dict[original_idx] 
                
                # Маппинг алиасов
                real_tag_name = ""
                if target_tag_alias == 'BODY': real_tag_name = 'BODY_START'
                elif target_tag_alias == 'EXIT': real_tag_name = 'LOOP_END'
                elif target_tag_alias == 'COND': real_tag_name = 'COND_START'
                
                # Получаем числовой адрес из карты
                target_addr = label_map.get(real_tag_name, 0)
                
                # Добавляем в финал числовой адрес (EntryType.ADDR, int)
                final_entries.append(Entry(EntryType.ADDR, target_addr))
                
            # --- Логика пропуска определения метки ---
            elif entry.type == EntryType.ADDR and isinstance(entry.data, str):
                # Пропускаем определения меток (COND_START, BODY_START, LOOP_END)
                pass 
                
            # --- Копирование обычных команд/операндов ---
            else:
                final_entries.append(entry)
                
            original_idx += 1
            
        self.entries = final_entries
        return self.entries

    def _poliz_generator(self, node: 'TreeNode'):
        # ... (Program/Loop - здесь нужно проверить индексы Condition и Body)
        
        # Для Program из ЛР2:
        # children: [Keyword(DO), Keyword(UNTIL), LogExpr, Statements, Keyword(LOOP)]
        if node.name == "Program":
             # Метка начала условия
            self.entries.append(Entry(EntryType.ADDR, "COND_START")) 
            
            # 1. Условие - это children[2] (LogExpr)
            self._poliz_generator(node.children[2]) 
            
            # 2. JZ / JMP
            addr_jz = len(self.entries)
            self.entries.append(Entry(EntryType.ADDR, "BODY")) 
            self.entries.append(Entry(EntryType.COMMAND, Command.JZ))
            self.jmp_patches.append((addr_jz, "BODY"))

            addr_jmp_exit = len(self.entries)
            self.entries.append(Entry(EntryType.ADDR, "EXIT")) 
            self.entries.append(Entry(EntryType.COMMAND, Command.JMP))
            self.jmp_patches.append((addr_jmp_exit, "EXIT"))

            # 3. Тело - это children[3] (Statements)
            self.entries.append(Entry(EntryType.ADDR, "BODY_START"))
            self._poliz_generator(node.children[3]) 

            # 4. Обратный JMP
            addr_jmp_cond = len(self.entries)
            self.entries.append(Entry(EntryType.ADDR, "COND")) 
            self.entries.append(Entry(EntryType.COMMAND, Command.JMP))
            self.jmp_patches.append((addr_jmp_cond, "COND"))

            # 5. Метка конца
            self.entries.append(Entry(EntryType.ADDR, "LOOP_END"))

        elif node.name == "Statements":
            # Ваша рекурсивная структура Statements -> Statement, Statements
            # просто обходим всех детей.
            for child in node.children:
                self._poliz_generator(child)

        elif node.name == "Assign":
            # children: [Var, Expr] (Op '=' не добавляется)
            # 1. Правая часть (Expr) - индекс 1
            self._poliz_generator(node.children[1]) 
            # 2. Имя переменной - индекс 0
            self.entries.append(Entry(EntryType.VARIABLE, node.children[0].value)) 
            # 3. MOV
            self.entries.append(Entry(EntryType.COMMAND, Command.MOV))
            
        elif node.name == "Input":
            # children: [Var] (Keyword и IO_OP не добавляются)
            # Имя переменной - индекс 0
            self.entries.append(Entry(EntryType.VARIABLE, node.children[0].value))
            self.entries.append(Entry(EntryType.COMMAND, Command.INPUT))
        
        elif node.name == "Output":
            # children: [Expr]
            # Выражение - индекс 0
            self._poliz_generator(node.children[0]) 
            self.entries.append(Entry(EntryType.COMMAND, Command.OUTPUT))

        # --- Логические операции (Logic, Not) ---
        elif node.name == "Logic": # AND/OR
            self._poliz_generator(node.children[0])
            self._poliz_generator(node.children[1])
            cmd_map = {'and': Command.AND, 'or': Command.OR}
            self.entries.append(Entry(EntryType.COMMAND, cmd_map.get(node.value)))
            
        elif node.name == "Not":
            self._poliz_generator(node.children[0])
            self.entries.append(Entry(EntryType.COMMAND, Command.NOT))

        # --- Блок сравнения (Cmp) ---
        elif node.name == "Cmp":
            self._poliz_generator(node.children[0])
            self._poliz_generator(node.children[1])
            op = node.value
            cmd_map = {'<': Command.CMPL, '>': Command.CMPG, '==': Command.CMPE, '<=': Command.CMPLE, '>=': Command.CMPGE, '<>': Command.CMPNE}
            self.entries.append(Entry(EntryType.COMMAND, cmd_map.get(op, Command.CMPE)))

        # --- Арифметические операции (Op) ---
        elif node.name == "Op":
            self._poliz_generator(node.children[0])
            self._poliz_generator(node.children[1])
            op = node.value
            cmd_map = {'+': Command.ADD, '-': Command.SUB, '*': Command.MUL, '/': Command.DIV}
            self.entries.append(Entry(EntryType.COMMAND, cmd_map.get(op)))

        # --- Операнды ---
        elif node.name == "Var":
            self.entries.append(Entry(EntryType.VARIABLE, node.value))
        elif node.name == "Const":
            self.entries.append(Entry(EntryType.CONSTANT, int(node.value)))
            
        # Узлы Keyword, Var, Const пропускаются, т.к. обработаны выше
        # Узлы ( ) пропускаются, т.к. они уже включены в AST как часть выражений.
        
    def _find_tag_addr(self, tag: str) -> int:
        for i, entry in enumerate(self.entries):
            if entry.type == EntryType.ADDR and entry.data == tag:
                return i
        return -1

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
        tree = parser.parse_program() # Построение AST
        print("Дерево разбора:")
        print(tree)
        print("Анализ успешен (построено AST)")
        
        # --- НОВЫЙ ШАГ: ГЕНЕРАЦИЯ ПОЛИЗ ---
        poliz_entries = parser.generate_poliz(tree)
        print("\nСгенерированный ПОЛИЗ:")
        print("-" * 60)
        print(" ".join(str(e) for e in poliz_entries))
        print("-" * 60)
            
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
