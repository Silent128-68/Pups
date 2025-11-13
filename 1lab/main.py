import re
import sys
from typing import List, Tuple, Dict, NamedTuple

class Lexeme(NamedTuple):
    value: str
    type: str
    category: str

# Ключевые слова
KEYWORDS = {
    'do': 'DO',
    'until': 'UNTIL',
    'loop': 'LOOP',
    'input': 'INPUT',
    'output': 'OUTPUT',
    'and': 'LOGICAL_OP',
    'or': 'LOGICAL_OP',
    'not': 'LOGICAL_NOT',
}

# Шаблон токенов (важен порядок)
TOKEN_SPECS = [
    ('NUMBER', r'\d+'),
    ('ID',     r'[A-Za-z][A-Za-z0-9_]*'),
    ('OP',     r'<<|<=|>=|==|<>|[<>=+\-*/;()=]'),
    ('SKIP',   r'[ \t\r\n]+'),
    ('MISMATCH', r'.'),
]

token_regex = re.compile('|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPECS))

def lex(input_text: str) -> Tuple[List[Lexeme], Dict[str,int], Dict[str,int]]:
    lexemes: List[Lexeme] = []
    id_table: Dict[str,int] = {}
    const_table: Dict[str,int] = {}
    next_id, next_const = 1, 1

    for mo in token_regex.finditer(input_text):
        kind = mo.lastgroup
        val = mo.group(0)
        if kind == 'NUMBER':
            lexemes.append(Lexeme(val, 'CONSTANT', 'constant'))
            if val not in const_table:
                const_table[val] = next_const
                next_const += 1
        elif kind == 'ID':
            low = val.lower()
            if low in KEYWORDS:
                lexemes.append(Lexeme(val, KEYWORDS[low], 'keyword'))
            else:
                lexemes.append(Lexeme(val, 'IDENTIFIER', 'identifier'))
                if low not in id_table:
                    id_table[low] = next_id
                    next_id += 1
        elif kind == 'OP':
            if val == ';':
                lexemes.append(Lexeme(val, 'SEMICOLON', 'symbol'))
            elif val in ('+', '-', '*', '/'):
                lexemes.append(Lexeme(val, 'ARITHMETIC', 'operation'))
            elif val in ('<=', '>=', '==', '<>', '<', '>'):
                lexemes.append(Lexeme(val, 'COMPARISON', 'operation'))
            elif val == '=':
                lexemes.append(Lexeme(val, 'ASSIGNMENT', 'operation'))
            elif val == '<<':
                lexemes.append(Lexeme(val, 'IO_OP', 'operation'))
            elif val in ('(', ')'):
                lexemes.append(Lexeme(val, 'PAREN', 'symbol'))
            else:
                lexemes.append(Lexeme(val, 'UNKNOWN_OP', 'operation'))
        elif kind == 'SKIP':
            continue
        elif kind == 'MISMATCH':
            lexemes.append(Lexeme(val, 'ERROR', 'invalid'))
            print(f"[LEX ERROR] недопустимый символ: {val!r}", file=sys.stderr)

    return lexemes, id_table, const_table

# --- Функции для вывода таблиц ---
def print_table(title: str, headers: list, rows: list):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))

    total_width = sum(widths) + len(widths) * 3 + 1
    print(f"\n{title}")
    print("─" * total_width)
    header_line = "│ " + " │ ".join(f"{h:<{w}}" for h, w in zip(headers, widths)) + " │"
    print(header_line)
    print("├" + "┼".join("─" * (w + 2) for w in widths) + "┤")

    for row in rows:
        print("│ " + " │ ".join(f"{str(v):<{w}}" for v, w in zip(row, widths)) + " │")

    print("─" * total_width)

def main():
    try:
        with open("FL_1lab_input.txt", "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print("Файл input.txt не найден.")
        return

    lexemes, id_table, const_table = lex(text)

    print("\nЛексический анализ программы")
    print("Исходный код:\n" + "─" * 50)
    print(text)
    print("─" * 50)

    # Таблица лексем
    rows = [(i+1, lx.value, lx.type, lx.category) for i, lx in enumerate(lexemes)]
    print_table("Таблица лексем", ["№", "Лексема", "Тип", "Категория"], rows)

    # Таблица идентификаторов
    rows_id = [(i, name) for name, i in sorted(id_table.items(), key=lambda kv: kv[1])]
    print_table("Таблица идентификаторов", ["№", "Идентификатор"], rows_id)

    # Таблица констант
    rows_c = [(i, val) for val, i in sorted(const_table.items(), key=lambda kv: kv[1])]
    print_table("Таблица констант", ["№", "Константа"], rows_c)

    print("\nАнализ успешно завершён!")

if __name__ == "__main__":
    main()
