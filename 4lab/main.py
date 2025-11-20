import sys
from enum import Enum
from typing import List, Tuple, Union, Dict

# ==========================================
# 1. СТРУКТУРЫ ДАННЫХ
# ==========================================

class LexemeType(Enum):
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    CONSTANT = "CONSTANT"
    ASSIGNMENT = "ASSIGNMENT"     # =
    RELATION = "RELATION"         # <, >, ==, etc
    ARITHMETIC = "ARITHMETIC"     # +, -, *, /
    IO_OP = "IO_OP"               # <<
    SEPARATOR = "SEPARATOR"       # ;

class Lexeme:
    def __init__(self, ltype: LexemeType, value: str):
        self.type = ltype
        self.value = value
    def __repr__(self): return f"{self.type.name} '{self.value}'"

class Command(Enum):
    JMP = "JMP"      # Безусловный переход
    JZ = "JZ"        # Переход, если ложь (0)
    MOV = "MOV"      # Присваивание
    ADD = "ADD"; SUB = "SUB"; MUL = "MUL"; DIV = "DIV"
    CMPL = "CMPL"; CMPG = "CMPG"; CMPE = "CMPE"; CMPNE = "CMPNE"; CMPLE = "CMPLE"; CMPGE = "CMPGE"
    INPUT = "INPUT"; OUTPUT = "OUTPUT"
    AND = "AND"; OR = "OR"; NOT = "NOT"

class EntryType(Enum):
    COMMAND = "COMMAND"
    VARIABLE = "VARIABLE"
    CONSTANT = "CONSTANT"
    ADDR = "ADDR"

class Entry:
    def __init__(self, etype: EntryType, data: Union[Command, str, int]):
        self.type = etype
        self.data = data
    def __repr__(self):
        if self.type == EntryType.COMMAND: return self.data.value
        return str(self.data)

# ==========================================
# 2. ЛЕКСИЧЕСКИЙ АНАЛИЗАТОР
# ==========================================

class LexicalAnalyzer:
    def __init__(self):
        self.keywords = {"do", "until", "loop", "input", "output", "and", "or", "not"}
        self.relations = {"<", ">", "==", "<>", "<=", ">="}
        self.arithmetic = {"+", "-", "*", "/"}
        
    def analyse(self, text: str) -> List[Lexeme]:
        lexemes = []
        i = 0
        n = len(text)
        while i < n:
            char = text[i]
            if char.isspace():
                i += 1; continue
            if char.isalpha():
                start = i
                while i < n and (text[i].isalnum() or text[i] == '_'): i += 1
                val = text[start:i]
                if val.lower() in self.keywords: lexemes.append(Lexeme(LexemeType.KEYWORD, val.lower()))
                else: lexemes.append(Lexeme(LexemeType.IDENTIFIER, val))
            elif char.isdigit():
                start = i
                while i < n and text[i].isdigit(): i += 1
                val = text[start:i]
                lexemes.append(Lexeme(LexemeType.CONSTANT, val))
            elif char == '<' and i+1 < n and text[i+1] == '<':
                 lexemes.append(Lexeme(LexemeType.IO_OP, "<<")); i += 2
            elif char in self.relations or char == '=':
                if i + 1 < n and text[i:i+2] in self.relations:
                    lexemes.append(Lexeme(LexemeType.RELATION, text[i:i+2])); i += 2
                elif char == '=':
                    lexemes.append(Lexeme(LexemeType.ASSIGNMENT, "=")); i += 1
                else:
                    lexemes.append(Lexeme(LexemeType.RELATION, char)); i += 1
            elif char in self.arithmetic:
                lexemes.append(Lexeme(LexemeType.ARITHMETIC, char)); i += 1
            elif char == ';':
                lexemes.append(Lexeme(LexemeType.SEPARATOR, ";")); i += 1
            else: i += 1 
        return lexemes

# ==========================================
# 3. СИНТАКСИЧЕСКИЙ АНАЛИЗАТОР (Генератор ПОЛИЗ)
# ==========================================

class SyntacticParser:
    def __init__(self):
        self.lexemes = []
        self.entries = []
        
    def parse(self, text: str) -> Tuple[List[Entry], bool]:
        lexer = LexicalAnalyzer()
        self.lexemes = lexer.analyse(text)
        self.entries = []
        if not self.lexemes: return [], False
        end_pos, success = self.do_until_loop(0, len(self.lexemes) - 1)
        return self.entries, success

    def do_until_loop(self, begin: int, end: int) -> Tuple[int, bool]:
        if self.lexemes[begin].value != 'do': return begin, False
        if self.lexemes[begin+1].value != 'until': return begin, False
        
        addr_start_cond = len(self.entries) # Адрес начала условия
        
        # Разбор условия
        current_pos, success = self.rel_expr(begin + 2, end)
        if not success: return current_pos, False
        
        # JZ -> Body (Если условие False, заходим в цикл)
        addr_jz = len(self.entries)
        self.entries.append(Entry(EntryType.ADDR, 0)) 
        self.entries.append(Entry(EntryType.COMMAND, Command.JZ))
        
        # JMP -> Exit (Если условие True, выходим)
        addr_jmp_exit = len(self.entries)
        self.entries.append(Entry(EntryType.ADDR, 0))
        self.entries.append(Entry(EntryType.COMMAND, Command.JMP))
        
        # Начало тела
        addr_body = len(self.entries)
        self.entries[addr_jz].data = addr_body # Backpatch JZ
        
        while current_pos <= end:
            if self.lexemes[current_pos].value == 'loop': break
            if self.lexemes[current_pos].type == LexemeType.SEPARATOR:
                current_pos += 1; continue

            # Присваивание
            if (self.lexemes[current_pos].type == LexemeType.IDENTIFIER and 
                current_pos + 1 <= end and self.lexemes[current_pos+1].type == LexemeType.ASSIGNMENT):
                var_name = self.lexemes[current_pos].value
                self.entries.append(Entry(EntryType.VARIABLE, var_name))
                self.entries.append(Entry(EntryType.VARIABLE, var_name)) # Копия для вычислений если нужно, но для MOV важнее порядок
                # Важно: для MOV нам нужно: VarName Value MOV
                # Но здесь мы парсим простую структуру.
                # Уберем лишнюю копию переменной, если она не нужна для вычисления правой части.
                # Правильная структура: VarName, [Выражение], MOV
                # Удалим вторую запись
                self.entries.pop() 
                
                expr_end, success = self.arith_expr(current_pos + 2, end)
                self.entries.append(Entry(EntryType.COMMAND, Command.MOV))
                current_pos = expr_end

            # INPUT
            elif (self.lexemes[current_pos].value == 'input' and self.lexemes[current_pos+1].type == LexemeType.IO_OP):
                var_name = self.lexemes[current_pos+2].value
                self.entries.append(Entry(EntryType.VARIABLE, var_name))
                self.entries.append(Entry(EntryType.COMMAND, Command.INPUT))
                current_pos += 3
            # OUTPUT
            elif (self.lexemes[current_pos].value == 'output' and self.lexemes[current_pos+1].type == LexemeType.IO_OP):
                var_name = self.lexemes[current_pos+2].value
                self.entries.append(Entry(EntryType.VARIABLE, var_name))
                self.entries.append(Entry(EntryType.COMMAND, Command.OUTPUT))
                current_pos += 3
            else: current_pos += 1
        
        # Прыжок в начало для проверки
        self.entries.append(Entry(EntryType.ADDR, addr_start_cond))
        self.entries.append(Entry(EntryType.COMMAND, Command.JMP))
        
        addr_end = len(self.entries)
        self.entries[addr_jmp_exit].data = addr_end # Backpatch JMP Exit
        
        return current_pos + 1, True

    def rel_expr(self, begin: int, end: int) -> Tuple[int, bool]:
        # Простая структура: Op Rel Op
        self.entries.append(Entry(EntryType.VARIABLE, self.lexemes[begin].value))
        op_val = self.lexemes[begin+2].value
        if self.lexemes[begin+2].type == LexemeType.IDENTIFIER:
             self.entries.append(Entry(EntryType.VARIABLE, op_val))
        else:
             self.entries.append(Entry(EntryType.CONSTANT, int(op_val)))
             
        rel = self.lexemes[begin+1].value
        cmd = Command.CMPE
        if rel == '>': cmd = Command.CMPG
        elif rel == '<': cmd = Command.CMPL
        elif rel == '>=': cmd = Command.CMPGE
        elif rel == '<=': cmd = Command.CMPLE
        elif rel == '<>': cmd = Command.CMPNE
        
        self.entries.append(Entry(EntryType.COMMAND, cmd))
        return begin + 3, True

    def arith_expr(self, begin: int, end: int) -> Tuple[int, bool]:
        # Простая структура: Op Arith Op
        # Операнд 1
        val1 = self.lexemes[begin].value
        if self.lexemes[begin].type == LexemeType.IDENTIFIER:
            self.entries.append(Entry(EntryType.VARIABLE, val1))
        else:
            self.entries.append(Entry(EntryType.CONSTANT, int(val1)))
        
        # Оператор
        op_sym = self.lexemes[begin+1].value
        
        # Операнд 2
        val2 = self.lexemes[begin+2].value
        if self.lexemes[begin+2].type == LexemeType.IDENTIFIER:
            self.entries.append(Entry(EntryType.VARIABLE, val2))
        else:
            self.entries.append(Entry(EntryType.CONSTANT, int(val2)))
            
        cmd = Command.ADD if op_sym == '+' else (Command.SUB if op_sym == '-' else (Command.MUL if op_sym == '*' else Command.DIV))
        self.entries.append(Entry(EntryType.COMMAND, cmd))
        return begin + 3, True

# ==========================================
# 4. ИНТЕРПРЕТАТОР
# ==========================================

class Interpreter:
    def __init__(self):
        self.parser = SyntacticParser()
        self.stack = []
        self.variables = {}
        
    def interpret(self, text: str) -> bool:
        entries, success = self.parser.parse(text)
        if not success:
            print("Ошибка генерации ПОЛИЗ")
            return False
        
        print("\nСгенерированный ПОЛИЗ:")
        print(" ".join(str(e) for e in entries))
        print("\n=== НАЧАЛО ВЫПОЛНЕНИЯ ===")
        
        ip = 0 # Указатель инструкции
        
        while ip < len(entries):
            entry = entries[ip]
            
            # Трассировка
            self.print_trace(ip, entry)
            
            if entry.type in (EntryType.CONSTANT, EntryType.VARIABLE, EntryType.ADDR):
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

    def get_value(self, item) -> int:
        """Превращает имя переменной в значение. Числа возвращает как есть."""
        if isinstance(item, int):
            return item
        if isinstance(item, str):
            return self.variables.get(item, 0) # 0 если переменная не инициализирована
        return 0

    def execute_command(self, cmd: Command, current_ip: int) -> Union[int, None]:
        if cmd == Command.MOV:
            val = self.get_value(self.stack.pop())
            var_name = self.stack.pop() # Здесь нужно имя, а не значение
            self.variables[var_name] = val
            
        elif cmd == Command.ADD:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(v1 + v2)
            
        elif cmd == Command.SUB:
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(v1 - v2)
            
        elif cmd == Command.CMPL: # <
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(1 if v1 < v2 else 0)

        elif cmd == Command.CMPG: # >
            v2 = self.get_value(self.stack.pop())
            v1 = self.get_value(self.stack.pop())
            self.stack.append(1 if v1 > v2 else 0)
            
        elif cmd == Command.JZ:
            addr = self.stack.pop()
            cond = self.get_value(self.stack.pop())
            if cond == 0: # Если Ложь
                return addr # Прыгаем
                
        elif cmd == Command.JMP:
            addr = self.stack.pop()
            return addr
            
        elif cmd == Command.INPUT:
            var_name = self.stack.pop()
            try:
                val = int(input(f"> Введите значение для '{var_name}': "))
                self.variables[var_name] = val
            except ValueError:
                print("Ошибка: введено не число, присвоено 0")
                self.variables[var_name] = 0

        elif cmd == Command.OUTPUT:
            val = self.get_value(self.stack.pop())
            print(f"> OUTPUT: {val}")
            
        return None

    def print_trace(self, ip, entry):
        stack_str = str(self.stack)
        print(f"[{ip:2}] {str(entry):<10} | Stack: {stack_str:<30} | Vars: {self.variables}")

# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    # Пример: do until x > 5 ...
    # Цикл будет работать пока x <= 5.
    code = """do until x > 5
      x = x + 1
      output << x
    loop"""
    
    print("Исходный код:")
    print(code)
    
    interpreter = Interpreter()
    interpreter.interpret(code)
