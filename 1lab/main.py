import re
import sys
from typing import List, Tuple, Dict, NamedTuple

# Req 1: Обновляем Lexeme, добавляя line и col
class Lexeme(NamedTuple):
    value: str
    type: str
    category: str
    line: int
    col: int

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

# Req 3: Обновляем TOKEN_SPECS
# Мы объединяем ID и NUMBER, чтобы правильно ловить ошибки типа '1output'
TOKEN_SPECS = [
    # Эта группа ДОЛЖНА быть первой.
    # 1. Валидный ID: [A-Za-z][A-Za-z0-9_]*
    # 2. Токен, начинающийся с цифры: \d+[A-Za-z0-9_]* (может быть валидным '123' или невалидным '123x')
    ('ID_OR_NUM', r'[A-Za-z][A-Za-z0-9_]*|\d+[A-Za-z0-9_]*'),
    
    # Операторы (порядок важен, от длинных к коротким)
    ('OP',        r'<<|<=|>=|==|<>|[<>=+\-*/;()=]'),
    
    # Пропуск пробелов
    ('SKIP',      r'[ \t\r]+'), # Убрали \n, так как обрабатываем построчно
    
    # Ошибка (любой другой одиночный символ)
    ('MISMATCH',  r'.'),
]

token_regex = re.compile('|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPECS))

def lex(line_text: str, line_num: int, id_table: Dict[str, int], const_table: Dict[str, int]) -> List[Lexeme]:
    """
    Анализирует одну строку текста.
    Заполняет id_table и const_table.
    Возвращает список лексем ИЛИ вызывает ValueError при ошибке.
    """
    lexemes: List[Lexeme] = []
    
    # Получаем текущие максимальные индексы для таблиц
    next_id = len(id_table) + 1
    next_const = len(const_table) + 1

    # Итерируемся по всем совпадениям в строке
    for mo in token_regex.finditer(line_text):
        kind = mo.lastgroup
        val = mo.group(0)
        col = mo.start() + 1 # +1 для нумерации столбцов с 1

        if kind == 'ID_OR_NUM':
            # Req 3: Логика для классификации ID, NUMBER или ОШИБКИ
            if val[0].isdigit():
                if val.isdigit():
                    # --- ВАЛИДНАЯ КОНСТАНТА ---
                    lexemes.append(Lexeme(val, 'CONSTANT', 'constant', line_num, col))
                    if val not in const_table:
                        const_table[val] = next_const
                        next_const += 1
                else:
                    # --- НЕВАЛИДНЫЙ ТОКЕН (напр. '1output') ---
                    # Req 2: Вызываем ошибку и останавливаемся
                    raise ValueError(f"Строка {line_num}, поз. {col}: Недопустимый токен (идентификатор не может начинаться с цифры): '{val}'")
            
            elif val[0].isalpha():
                # --- ВАЛИДНЫЙ ID или KEYWORD ---
                low = val.lower()
                if low in KEYWORDS:
                    lexemes.append(Lexeme(val, KEYWORDS[low], 'keyword', line_num, col))
                else:
                    lexemes.append(Lexeme(val, 'IDENTIFIER', 'identifier', line_num, col))
                    if low not in id_table:
                        id_table[low] = next_id
                        next_id += 1
        
        elif kind == 'OP':
            # Логика классификации операторов (осталась прежней)
            op_type, op_cat = 'UNKNOWN_OP', 'operation' # По умолчанию
            if val == ';':
                op_type, op_cat = 'SEMICOLON', 'symbol'
            elif val in ('+', '-', '*', '/'):
                op_type, op_cat = 'ARITHMETIC', 'operation'
            elif val in ('<=', '>=', '==', '<>', '<', '>'):
                op_type, op_cat = 'COMPARISON', 'operation'
            elif val == '=':
                op_type, op_cat = 'ASSIGNMENT', 'operation'
            elif val == '<<':
                op_type, op_cat = 'IO_OP', 'operation'
            elif val in ('(', ')'):
                op_type, op_cat = 'PAREN', 'symbol'
            
            lexemes.append(Lexeme(val, op_type, op_cat, line_num, col))
            
        elif kind == 'SKIP':
            continue # Просто пропускаем пробелы

        elif kind == 'MISMATCH':
            # Req 2: Вызываем ошибку и останавливаемся
            raise ValueError(f"Строка {line_num}, поз. {col}: Недопустимый символ: {val!r}")

    return lexemes

# --- Функции для вывода таблиц ---

# Req 1: Обновляем print_table для вывода позиции
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
        print("❌ Файл FL_1lab_input.txt не найден.")
        return

    print("\n📘 Лексический анализ программы")
    print("Исходный код:\n" + "─" * 50)
    print(text)
    print("─" * 50)

    all_lexemes: List[Lexeme] = []
    id_table: Dict[str, int] = {}
    const_table: Dict[str, int] = {}

    # Req 2: Оборачиваем анализ в try...except
    try:
        # Анализируем построчно
        lines = text.splitlines()
        for line_num, line_text in enumerate(lines, 1):
            # Передаем таблицы, чтобы они наполнялись
            lexemes_on_line = lex(line_text, line_num, id_table, const_table)
            all_lexemes.extend(lexemes_on_line)
            
    except ValueError as e:
        # Ловим первую же лексическую ошибку и прерываем анализ
        print(f"❌ ОШИБКА ЛЕКСИЧЕСКОГО АНАЛИЗА:")
        print(e)
        print("\nАнализ прерван.")
        sys.exit(1) # Выход с кодом ошибки

    # --- Если ошибок не было, печатаем таблицы ---

    # Таблица лексем
    # Req 1: Добавляем "Позиция" в вывод
    rows = []
    for i, lx in enumerate(all_lexemes):
        pos = f"Строка {lx.line}, поз. {lx.col}"
        rows.append((i + 1, lx.value, lx.type, lx.category, pos))
        
    print_table("Таблица лексем", ["№", "Лексема", "Тип", "Категория", "Позиция"], rows)

    # Таблица идентификаторов
    rows_id = [(i, name) for name, i in sorted(id_table.items(), key=lambda kv: kv[1])]
    print_table("Таблица идентификаторов", ["№", "Идентификатор"], rows_id)

    # Таблица констант
    rows_c = [(i, val) for val, i in sorted(const_table.items(), key=lambda kv: kv[1])]
    print_table("Таблица констант", ["№", "Константа"], rows_c)

    print("\n✅ Анализ успешно завершён!")

if __name__ == "__main__":
    main()
