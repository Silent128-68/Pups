import sys
from enum import Enum
from typing import List, Tuple, Union

class LexemeType(Enum):
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    CONSTANT = "CONSTANT"
    ASSIGNMENT = "ASSIGNMENT"
    RELATION = "RELATION"
    ARITHMETIC_SIMPLE = "ARITHMETIC_SIMPLE"
    SEPARATOR = "SEPARATOR"
    IO_OP = "IO_OP"

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
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    CMPL = "CMPL"
    CMPG = "CMPG"
    CMPE = "CMPE"
    CMPNE = "CMPNE"
    CMPLE = "CMPLE"
    CMPGE = "CMPGE"
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

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

class LexicalAnalyzer:
    def __init__(self):
        self.keywords = {"do", "until", "loop", "input", "output"}
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
            
            if char.isalpha():
                start = i
                while i < n and (text[i].isalnum() or text[i] == '_'):
                    i += 1
                val = text[start:i]
                if val.lower() in self.keywords:
                    lexemes.append(Lexeme(LexemeType.KEYWORD, val.lower()))
                else:
                    lexemes.append(Lexeme(LexemeType.IDENTIFIER, val))
            
            elif char.isdigit():
                start = i
                while i < n and text[i].isdigit():
                    i += 1
                val = text[start:i]
                lexemes.append(Lexeme(LexemeType.CONSTANT, val))
            
            elif char == '<' and i+1 < n and text[i+1] == '<':
                 lexemes.append(Lexeme(LexemeType.IO_OP, "<<"))
                 i += 2

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
                    
            elif char in self.arithmetic:
                lexemes.append(Lexeme(LexemeType.ARITHMETIC_SIMPLE, char))
                i += 1
            elif char == ';':
                lexemes.append(Lexeme(LexemeType.SEPARATOR, ";"))
                i += 1
            else:
                i += 1 
                
        return lexemes

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
        
        if not self.lexemes:
            return False
            
        end_pos, success = self.do_until_loop(0, len(self.lexemes) - 1)
        return success

    def do_until_loop(self, begin: int, end: int) -> Tuple[int, bool]:
        print(f"do_until_loop: begin={begin}, end={end}")
        
        if self.lexemes[begin].value != 'do': return begin, False
        if self.lexemes[begin+1].value != 'until': return begin, False
            
        addr_start_cond = len(self.entries)
        cond_pos = begin + 2
        
        current_pos, success = self.rel_expr(cond_pos, end)
        
        # JZ -> Body
        addr_jz = len(self.entries)
        self.entries.append(Entry(EntryType.ADDR, 0))
        self.entries.append(Entry(EntryType.COMMAND, Command.JZ))
        
        # JMP -> Exit
        addr_jmp_exit = len(self.entries)
        self.entries.append(Entry(EntryType.ADDR, 0))
        self.entries.append(Entry(EntryType.COMMAND, Command.JMP))
        
        addr_body = len(self.entries)
        self.entries[addr_jz].data = addr_body
        
        while current_pos <= end:
            if self.lexemes[current_pos].value == 'loop': break
            
            print(f"Обработка инструкции на позиции {current_pos}")
            if self.lexemes[current_pos].type == LexemeType.SEPARATOR:
                current_pos += 1; continue

            if (self.lexemes[current_pos].type == LexemeType.IDENTIFIER and 
                self.lexemes[current_pos+1].type == LexemeType.ASSIGNMENT):
                var_name = self.lexemes[current_pos].value
                self.entries.append(Entry(EntryType.VARIABLE, var_name))
                self.entries.append(Entry(EntryType.VARIABLE, var_name))
                self.entries.pop() 
                
                expr_end, success = self.arith_expr(current_pos + 2, end)
                self.entries.append(Entry(EntryType.COMMAND, Command.MOV))
                current_pos = expr_end
            
            # Input
            elif (self.lexemes[current_pos].value == 'input'):
                var = self.lexemes[current_pos+2].value
                self.entries.append(Entry(EntryType.VARIABLE, var))
                self.entries.append(Entry(EntryType.COMMAND, Command.INPUT))
                current_pos += 3
            
            # Output
            elif (self.lexemes[current_pos].value == 'output'):
                var = self.lexemes[current_pos+2].value
                self.entries.append(Entry(EntryType.VARIABLE, var))
                self.entries.append(Entry(EntryType.COMMAND, Command.OUTPUT))
                current_pos += 3
            
            else: current_pos += 1
        
        self.entries.append(Entry(EntryType.ADDR, addr_start_cond))
        self.entries.append(Entry(EntryType.COMMAND, Command.JMP))
        
        addr_end = len(self.entries)
        self.entries[addr_jmp_exit].data = addr_end
        
        print(f"Успешно завершен разбор цикла. Конец: {current_pos}")
        return current_pos, True

    def rel_expr(self, begin: int, end: int) -> Tuple[int, bool]:
        print(f"rel_expr: begin={begin}, end={end}")
        self.entries.append(Entry(EntryType.VARIABLE, self.lexemes[begin].value))
        val2 = self.lexemes[begin+2].value
        if self.lexemes[begin+2].type == LexemeType.IDENTIFIER:
            self.entries.append(Entry(EntryType.VARIABLE, val2))
        else:
            self.entries.append(Entry(EntryType.CONSTANT, int(val2)))
            
        op = self.lexemes[begin+1].value
        cmd = Command.CMPE
        if op == '>': cmd = Command.CMPG
        elif op == '<': cmd = Command.CMPL
        self.entries.append(Entry(EntryType.COMMAND, cmd))
        return begin + 3, True

    def arith_expr(self, begin: int, end: int) -> Tuple[int, bool]:
        print(f"arith_expr: begin={begin}, end={end}")
        op1 = self.lexemes[begin]
        if op1.type == LexemeType.IDENTIFIER: self.entries.append(Entry(EntryType.VARIABLE, op1.value))
        else: self.entries.append(Entry(EntryType.CONSTANT, int(op1.value)))
        
        op2 = self.lexemes[begin+2]
        if op2.type == LexemeType.IDENTIFIER: self.entries.append(Entry(EntryType.VARIABLE, op2.value))
        else: self.entries.append(Entry(EntryType.CONSTANT, int(op2.value)))
        
        sym = self.lexemes[begin+1].value
        cmd = Command.ADD if sym == '+' else Command.SUB
        self.entries.append(Entry(EntryType.COMMAND, cmd))
        return begin + 3, True

def main():
    filename = "FL_1lab_input.txt"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Ошибка: Файл '{filename}' не найден. Создайте файл с кодом программы.")
        return

    print(f"Исходный код из файла {filename}:")
    print("-" * 40)
    print(text)
    print("-" * 40)
    
    print("Выполняю анализ...")
    parser = SyntacticParser()
    success = parser.parse(text)
    
    if success:
        print("\nРезультат: УСПЕШНЫЙ АНАЛИЗ")
        print("Сгенерированный ПОЛИЗ:")
        print("-" * 60)
        print(" ".join(str(e) for e in parser.entries))
        print("-" * 60)
    else:
        print("Ошибка анализа")

if __name__ == "__main__":
    main()
