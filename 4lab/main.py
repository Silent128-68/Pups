import re
import sys
from enum import Enum
from typing import Union, Optional, List, Dict, NamedTuple, Tuple

# --- КЛАССЫ ИЗ ЛР3 (Lexeme, Entry, Command, EntryType) ---

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
    ('OP',          r'<<|<=|>=|==|<>|[<>=+\-*/;()=]'),
    ('SKIP',        r'[ \t\r]+'), 
    ('MISMATCH',    r'.'),
]

class Command(Enum):
    JMP = "JMP"; JZ = "JZ"; MOV = "MOV"
    ADD = "ADD"; SUB = "SUB"; MUL = "MUL"; DIV = "DIV"
    CMPL = "CMPL"; CMPG = "CMPG"; CMPE = "CMPE"; CMPNE = "CMPNE"; CMPLE = "CMPLE"; CMPGE = "CMPGE"
    INPUT = "INPUT"; OUTPUT = "OUTPUT"
    AND = "AND"; OR = "OR"; NOT = "NOT"

class EntryType(Enum):
    COMMAND = "COMMAND"; VARIABLE = "VARIABLE"; CONSTANT = "CONSTANT"; ADDR = "ADDR"

class Entry:
    def __init__(self, etype: EntryType, data: Union[Command, str, int]):
        self.type = etype
        self.data = data
    def __repr__(self):
        if self.type == EntryType.COMMAND: return self.data.value
        return str(self.data)

# --- ЛЕКСЕР (из ЛР3) ---

token_regex = re.compile('|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPECS))

def lex(line_text: str, line_num: int) -> List[Lexeme]:
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

# --- ПАРСЕР И ГЕНЕРАТОР ПОЛИЗ (из ЛР3) ---

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
    
    # --- МЕТОД ГЕНЕРАЦИИ ПОЛИЗ ИЗ ЛР3 (с патчем) ---
    def generate_poliz(self, node: 'TreeNode') -> List[Entry]:
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
            for child in node.children:
                self._poliz_generator(child)

        elif node.name == "Assign":
            # 1. Правая часть (Expr) - индекс 1
            self._poliz_generator(node.children[1]) 
            # 2. Имя переменной - индекс 0
            self.entries.append(Entry(EntryType.VARIABLE, node.children[0].value)) 
            # 3. MOV
            self.entries.append(Entry(EntryType.COMMAND, Command.MOV))
            
        elif node.name == "Input":
            # Имя переменной - индекс 0
            self.entries.append(Entry(EntryType.VARIABLE, node.children[0].value))
            self.entries.append(Entry(EntryType.COMMAND, Command.INPUT))
        
        elif node.name == "Output":
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
            # Важно: Константа должна быть int для интерпретатора
            self.entries.append(Entry(EntryType.CONSTANT, int(node.value)))


# --- ИНТЕРПРЕТАТОР (из ЛР4) ---

class Interpreter:
    # Убираем SyntacticParser, т.к. будем использовать RecursiveDescentParser
    def __init__(self):
        self.parser: Optional[RecursiveDescentParser] = None
        self.stack: List[Union[str, int]] = [] # Стек может хранить имена переменных (str) или значения (int)
        self.variables: Dict[str, int] = {}
        
    def interpret(self, code: str) -> bool:
        tokens = []
        try:
            for i, line in enumerate(code.splitlines(), 1):
                tokens.extend(lex(line, i))
            
            self.parser = RecursiveDescentParser(tokens)
            tree = self.parser.parse_program() # Построение AST
            
            print("\n--- Дерево разбора (AST) ---")
            print(tree)
            
            # *** Ключевой шаг: Генерация ПОЛИЗ из AST ***
            entries = self.parser.generate_poliz(tree)
            
        except Exception as e:
            print(f"Ошибка при анализе или генерации ПОЛИЗ: {e}")
            return False

        print("\nСгенерированный ПОЛИЗ:")
        print("-" * 60)
        print(" ".join(str(e) for e in entries))
        print("-" * 60)
        print("\n=== НАЧАЛО ВЫПОЛНЕНИЯ ===")
        
        ip = 0 
        
        while ip < len(entries):
            entry = entries[ip]
            
            self.print_trace(ip, entry)
            
            if entry.type in (EntryType.CONSTANT, EntryType.VARIABLE, EntryType.ADDR):
                # Добавляем данные (число, имя переменной или адрес) на стек
                self.stack.append(entry.data)
                ip += 1
            elif entry.type == EntryType.COMMAND:
                new_ip = self.execute_command(entry.data, ip)
                if new_ip is not None:
                    ip = new_ip
                else:
                    ip += 1
        
        print("\n=== КОНЕЦ ВЫПОЛНЕНИЯ ===")
        print("Финальные значения переменных:", self.variables)
        return True

    # Функция get_value остается прежней
    def get_value(self, item: Union[str, int]) -> int:
        # Если это int (константа или результат операции), возвращаем его
        if isinstance(item, int): return item
        # Если это str (имя переменной), возвращаем ее значение.
        # Если переменная не найдена, предполагаем 0 (или можно кинуть ошибку)
        if isinstance(item, str): return self.variables.get(item, 0)
        return 0

    def execute_command(self, cmd: Command, current_ip: int) -> Union[int, None]:
        # ВАЖНО: При работе с ПОЛИЗ, операнды всегда извлекаются со стека в порядке LIFO.
        # Для бинарных операций (ADD, CMPG и т.д.) порядок: v2 = pop(), v1 = pop().
        
        if cmd == Command.MOV:
            # Стек: [..., VALUE, VAR_NAME] -> VALUE = pop(), VAR_NAME = pop()
            # В вашем коде: var_name = self.stack.pop(), val = self.get_value(self.stack.pop())
            # Это неверно для ПОЛИЗ, где MOV: [RHS_VALUE, LHS_VAR_NAME] MOV
            
            # Правильный порядок:
            var_name = self.stack.pop()
            val = self.get_value(self.stack.pop()) # Значение (RHS)
            
            self.variables[var_name] = val
            
        # --- Арифметика ---
        elif cmd == Command.ADD:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(v1 + v2)
        elif cmd == Command.SUB:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(v1 - v2)
        elif cmd == Command.MUL:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(v1 * v2)
        elif cmd == Command.DIV:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(v1 // v2) # Целочисленное деление

        # --- Сравнения (результат: 1/0) ---
        elif cmd == Command.CMPL:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(1 if v1 < v2 else 0)
        elif cmd == Command.CMPG:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(1 if v1 > v2 else 0)
        # Добавьте недостающие команды сравнения
        elif cmd == Command.CMPE:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(1 if v1 == v2 else 0)
        elif cmd == Command.CMPNE:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(1 if v1 != v2 else 0)
        elif cmd == Command.CMPLE:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(1 if v1 <= v2 else 0)
        elif cmd == Command.CMPGE:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(1 if v1 >= v2 else 0)

        # --- Логические операции (Добавьте их, если они используются) ---
        elif cmd == Command.AND:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(1 if (v1 != 0 and v2 != 0) else 0)
        elif cmd == Command.OR:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(1 if (v1 != 0 or v2 != 0) else 0)
        elif cmd == Command.NOT:
            v = self.get_value(self.stack.pop())
            self.stack.append(1 if v == 0 else 0)
            
        # --- Переходы ---
        elif cmd == Command.JZ:
            # Стек: [..., CONDITION, ADDR] -> ADDR = pop(), CONDITION = pop()
            addr = self.stack.pop() # Адрес перехода (число)
            cond = self.get_value(self.stack.pop()) # Результат сравнения (0 или 1)
            if cond == 0: 
                return addr # Переходим по адресу
        elif cmd == Command.JMP:
            # Стек: [..., ADDR] -> ADDR = pop()
            addr = self.stack.pop() # Адрес перехода (число)
            return addr

        # --- Ввод/Вывод ---
        elif cmd == Command.INPUT:
            # Стек: [..., VAR_NAME] -> VAR_NAME = pop()
            var_name = self.stack.pop()
            try:
                # Ввод должен быть числом
                val = int(input(f"> Введите значение для '{var_name}': "))
                self.variables[var_name] = val
            except ValueError: 
                print("Ввод не число. Установлено значение 0.")
                self.variables[var_name] = 0
                
        elif cmd == Command.OUTPUT:
            # Стек: [..., VALUE] -> VALUE = pop()
            # В ПОЛИЗ Output: [EXPR_RESULT] OUTPUT
            val = self.get_value(self.stack.pop())
            print(f"> OUTPUT: {val}")
            
        return None

    def print_trace(self, ip, entry):
        stack_str = str(self.stack)
        # Убедимся, что все в self.variables — это int
        vars_display = {k: v for k, v in self.variables.items()}
        print(f"[{ip:2}] {str(entry):<10} | Stack: {stack_str:<30} | Vars: {vars_display}")

# --- ФУНКЦИЯ MAIN (из ЛР4) ---

def main():
    filename = "FL_1lab_input.txt"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        # Используем тестовый код, если файл не найден (как в ЛР3)
        print("Файл не найден. Использую тест: 'do until x > 5; x = x + 1; output << x; loop'")
        code = "do until x > 5; x = x + 1; output << x; loop"

    print(f"Исходный код:")
    print("-" * 40)
    print(code)
    print("-" * 40)
    
    # Инициализируем 'x' для теста, чтобы избежать ошибки при первом сравнении
    interpreter = Interpreter()
    interpreter.variables['x'] = 0 
    
    interpreter.interpret(code)

if __name__ == "__main__":
    main()
