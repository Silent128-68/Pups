import sys
from enum import Enum
from typing import List, Tuple, Union

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
    
    def __repr__(self):
        return f"{self.type.value} '{self.value}'"

class Command(Enum):
    JMP = "JMP"
    JZ = "JZ"
    MOV = "MOV"
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
        if self.type == EntryType.COMMAND:
            return self.data.value
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
                i += 1
                continue
            
            # Идентификаторы и ключевые слова
            if char.isalpha():
                start = i
                while i < n and (text[i].isalnum() or text[i] == '_'):
                    i += 1
                val = text[start:i]
                if val.lower() in self.keywords:
                    lexemes.append(Lexeme(LexemeType.KEYWORD, val.lower()))
                else:
                    lexemes.append(Lexeme(LexemeType.IDENTIFIER, val))
            
            # Числа
            elif char.isdigit():
                start = i
                while i < n and text[i].isdigit():
                    i += 1
                val = text[start:i]
                lexemes.append(Lexeme(LexemeType.CONSTANT, val))
            
            # Операторы ввода/вывода <<
            elif char == '<' and i+1 < n and text[i+1] == '<':
                 lexemes.append(Lexeme(LexemeType.IO_OP, "<<"))
                 i += 2

            # Операторы сравнения и присваивания
            elif char in self.relations or char == '=':
                if i + 1 < n and text[i:i+2] in self.relations:
                    lexemes.append(Lexeme(LexemeType.RELATION, text[i:i+2]))
                    i += 2
                elif char == '=':
                    lexemes.append(Lexeme(LexemeType.ASSIGNMENT, "="))
                    i += 1
                else:
                    lexemes.append(Lexeme(LexemeType.RELATION, char))
                    i += 1
            
            # Арифметика
            elif char in self.arithmetic:
                lexemes.append(Lexeme(LexemeType.ARITHMETIC, char))
                i += 1
            
            # Разделители
            elif char == ';':
                lexemes.append(Lexeme(LexemeType.SEPARATOR, ";"))
                i += 1
                
            else:
                i += 1 # Пропуск мусора
                
        return lexemes

# ==========================================
# 3. СИНТАКСИЧЕСКИЙ АНАЛИЗАТОР (DO UNTIL)
# ==========================================

class SyntacticParser:
    def __init__(self):
        self.lexemes = []
        self.entries = []
        
    def parse(self, text: str):
        lexer = LexicalAnalyzer()
        self.lexemes = lexer.analyse(text)
        self.entries = []
        
        print(f"Найдено лексем: {len(self.lexemes)}")
        for idx, lex in enumerate(self.lexemes):
            print(f"  {idx}: {lex}")
            
        if not self.lexemes: return False
        
        # Запуск разбора главной конструкции
        end_pos, success = self.do_until_loop(0, len(self.lexemes) - 1)
        return success

    # Грамматика: do until <condition> <statements> loop
    def do_until_loop(self, begin: int, end: int) -> Tuple[int, bool]:
        print(f"do_until_loop: begin={begin}, end={end}")
        
        # 1. Проверка 'do'
        if self.lexemes[begin].value != 'do':
            print("Ошибка: ожидалось 'do'")
            return begin, False
        
        # 2. Проверка 'until'
        if self.lexemes[begin+1].value != 'until':
            print("Ошибка: ожидалось 'until'")
            return begin, False
            
        # Адрес начала условия (куда прыгать в конце цикла)
        addr_start_cond = len(self.entries)
        
        # 3. Разбор условия (Logical Expression)
        # Предполагаем, что условие идет сразу после until
        cond_start = begin + 2
        # Ищем конец условия (до начала операторов или ключевых слов)
        # Упрощение: ищем операцию сравнения и операнды
        # В данном примере парсим простое сравнение: x > 10
        
        current_pos, success = self.rel_expr(cond_start, end)
        if not success: return current_pos, False
        
        # ЛОГИКА UNTIL: Выполнять ПОКА ЛОЖЬ.
        # Если True -> Выход (JMP Exit).
        # Если False -> Тело (JZ Body).
        
        # Резервируем адрес перехода в ТЕЛО (если False - 0)
        addr_jz_to_body = len(self.entries)
        self.entries.append(Entry(EntryType.ADDR, 0)) # Placeholder
        self.entries.append(Entry(EntryType.COMMAND, Command.JZ))
        
        # Если JZ не сработал (значит True, 1), идем на ВЫХОД
        addr_jmp_exit = len(self.entries)
        self.entries.append(Entry(EntryType.ADDR, 0)) # Placeholder
        self.entries.append(Entry(EntryType.COMMAND, Command.JMP))
        
        # Это адрес начала ТЕЛА (сюда прыгнет JZ)
        addr_body_start = len(self.entries)
        # Бэкпэтчинг (заполняем адрес в JZ)
        self.entries[addr_jz_to_body].data = addr_body_start
        
        # 4. Разбор тела цикла (Statements) до 'loop'
        while current_pos <= end:
            if self.lexemes[current_pos].value == 'loop':
                break
            
            print(f"Обработка инструкции на позиции {current_pos}")
            # Пропуск ;
            if self.lexemes[current_pos].type == LexemeType.SEPARATOR:
                current_pos += 1
                continue

            # Присваивание: ID = Expr
            if (self.lexemes[current_pos].type == LexemeType.IDENTIFIER and 
                current_pos + 1 <= end and 
                self.lexemes[current_pos+1].type == LexemeType.ASSIGNMENT):
                
                var_name = self.lexemes[current_pos].value
                self.entries.append(Entry(EntryType.VARIABLE, var_name)) # Куда
                self.entries.append(Entry(EntryType.VARIABLE, var_name)) # Для вычисления (упрощенно)
                
                # Парсим выражение справа от =
                expr_end, success = self.arith_expr(current_pos + 2, end)
                self.entries.append(Entry(EntryType.COMMAND, Command.MOV))
                current_pos = expr_end

            # INPUT << ID
            elif (self.lexemes[current_pos].value == 'input' and 
                  self.lexemes[current_pos+1].type == LexemeType.IO_OP):
                var_name = self.lexemes[current_pos+2].value
                self.entries.append(Entry(EntryType.VARIABLE, var_name))
                self.entries.append(Entry(EntryType.COMMAND, Command.INPUT))
                current_pos += 3

            # OUTPUT << Expr
            elif (self.lexemes[current_pos].value == 'output' and 
                  self.lexemes[current_pos+1].type == LexemeType.IO_OP):
                # Упрощенно: выводим переменную
                var_name = self.lexemes[current_pos+2].value
                self.entries.append(Entry(EntryType.VARIABLE, var_name))
                self.entries.append(Entry(EntryType.COMMAND, Command.OUTPUT))
                current_pos += 3
            
            else:
                current_pos += 1
        
        # 5. Проверка 'loop'
        if current_pos > end or self.lexemes[current_pos].value != 'loop':
             print("Ошибка: ожидалось 'loop'")
             return current_pos, False
             
        # В конце тела - безусловный прыжок на проверку условия
        self.entries.append(Entry(EntryType.ADDR, addr_start_cond))
        self.entries.append(Entry(EntryType.COMMAND, Command.JMP))
        
        # Это адрес ВЫХОДА (сюда прыгнет JMP, если условие было True)
        addr_program_end = len(self.entries)
        # Бэкпэтчинг (заполняем адрес в JMP Exit)
        self.entries[addr_jmp_exit].data = addr_program_end
        
        print(f"Успешно завершен разбор цикла do-until. Конец: {current_pos}")
        return current_pos, True

    def rel_expr(self, begin: int, end: int) -> Tuple[int, bool]:
        print(f"rel_expr: begin={begin}, end={end}")
        # Упрощенный парсер: Op Rel Op
        # 1. Операнд
        self.entries.append(Entry(EntryType.VARIABLE, self.lexemes[begin].value))
        # 2. Операция
        rel_op = self.lexemes[begin+1].value
        # 3. Операнд
        self.entries.append(Entry(EntryType.CONSTANT, self.lexemes[begin+2].value))
        
        cmd = Command.CMPE
        if rel_op == '>': cmd = Command.CMPG
        elif rel_op == '<': cmd = Command.CMPL
        elif rel_op == '<=': cmd = Command.CMPLE
        elif rel_op == '>=': cmd = Command.CMPGE
        
        self.entries.append(Entry(EntryType.COMMAND, cmd))
        return begin + 3, True

    def arith_expr(self, begin: int, end: int) -> Tuple[int, bool]:
        print(f"arith_expr: begin={begin}, end={end}")
        # Парсим простую арифметику: op arith_op op
        # x = x + 1 -> мы здесь парсим "x + 1"
        # "x" уже был добавлен вызывающей функцией (как часть MOV), 
        # но для ADD нам нужны оба операнда в стеке.
        
        # Т.к. в `do_until` мы добавили `VAR x` дважды, считаем, что левый операнд уже в стеке?
        # Нет, ПОЛИЗ для "x + 1" -> "x 1 ADD".
        # Исправим логику в `do_until`: там добавляется `VAR x` (цель) и всё.
        # Здесь добавляем операнд 1.
        
        # Операнд 1
        op1 = self.lexemes[begin]
        if op1.type == LexemeType.IDENTIFIER:
             self.entries.append(Entry(EntryType.VARIABLE, op1.value))
        else:
             self.entries.append(Entry(EntryType.CONSTANT, op1.value))
             
        # Операция
        op_sym = self.lexemes[begin+1].value
        
        # Операнд 2
        op2 = self.lexemes[begin+2]
        if op2.type == LexemeType.IDENTIFIER:
             self.entries.append(Entry(EntryType.VARIABLE, op2.value))
        else:
             self.entries.append(Entry(EntryType.CONSTANT, op2.value))
             
        cmd = Command.ADD if op_sym == '+' else Command.SUB
        self.entries.append(Entry(EntryType.COMMAND, cmd))
        
        return begin + 3, True

# ==========================================
# MAIN
# ==========================================

def main():
    # Пример с DO UNTIL
    text = """do until x > 10
      x = x + 1
      input << a;
      y = y - 2
    loop"""
    
    print("Исходный код:")
    print("-" * 40)
    print(text)
    print("-" * 40)
    
    print("Выполняю анализ...")
    parser = SyntacticParser()
    success = parser.parse(text)
    
    if success:
        print("\n✅ Результат: УСПЕШНЫЙ АНАЛИЗ")
        print("Сгенерированный ПОЛИЗ:")
        print("-" * 60)
        # Формат вывода в одну строку
        print(" ".join(str(e) for e in parser.entries))
        print("-" * 60)
        
        # Дешифровка адресов для проверки
        print("\nРасшифровка (индексы):")
        for i, e in enumerate(parser.entries):
            print(f"{i}: {e}")
    else:
        print("Ошибка анализа")

if __name__ == "__main__":
    main()
