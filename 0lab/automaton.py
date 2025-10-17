import json
import os
from collections import deque

# Константа для обозначения эпсилон-перехода
EPSILON = "epsilon"

class FiniteAutomaton:
    """Базовый класс для конечных автоматов."""

    def __init__(self, states, alphabet, transitions, start_state, final_states):
        self.states = set(states)
        self.alphabet = set(alphabet)
        self.transitions = transitions
        self.start_state = start_state
        self.final_states = set(final_states)
        self.validate()

    def validate(self):
        """Проверяет корректность автомата, выводит ошибки и предупреждения."""
        print("--- Проверка автомата ---")
        errors = []
        warnings = []

        if self.start_state not in self.states:
            errors.append(f"Ошибка: Стартовое состояние '{self.start_state}' отсутствует в списке состояний.")

        for state in self.final_states:
            if state not in self.states:
                errors.append(f"Ошибка: Конечное состояние '{state}' отсутствует в списке состояний.")

        for from_state, trans in self.transitions.items():
            if from_state not in self.states:
                errors.append(f"Ошибка: Состояние '{from_state}' из переходов не объявлено в списке состояний.")
            for symbol, to_states in trans.items():
                if symbol != EPSILON and symbol not in self.alphabet:
                    warnings.append(f"Предупреждение: Символ '{symbol}' из перехода не объявлен в алфавите.")
                
                # Для DFA to_states - строка, для NFA - список
                targets = to_states if isinstance(to_states, list) else [to_states]
                for state in targets:
                    if state not in self.states:
                        errors.append(f"Ошибка: Состояние '{state}' (результат перехода) не объявлено в списке состояний.")
        
        # Проверка на неполные переходы (только как предупреждение)
        for state in self.states:
            if state not in self.transitions:
                warnings.append(f"Предупреждение: Для состояния '{state}' не определено ни одного перехода.")
            else:
                for symbol in self.alphabet:
                    if symbol not in self.transitions.get(state, {}):
                         warnings.append(f"Предупреждение: Для состояния '{state}' не определен переход по символу '{symbol}'.")

        if errors:
            print("\nОбнаружены критические ошибки:")
            for e in errors:
                print(f"  - {e}")
            raise ValueError("Автомат сконфигурирован некорректно. Работа невозможна.")
        
        if warnings:
            print("\nОбнаружены предупреждения (автомат может работать некорректно):")
            for w in warnings:
                print(f"  - {w}")
        
        print("\n--- Проверка завершена ---")


    def display_transition_table(self):
        """Красиво выводит таблицу переходов в консоль."""
        print("\n--- Таблица переходов ---")
        
        # Определяем все символы для заголовков, включая эпсилон если он есть
        header_symbols = sorted(list(self.alphabet))
        if any(EPSILON in trans for trans in self.transitions.values()):
            header_symbols.insert(0, EPSILON)

        header = f"{'Состояние':>15} |" + "".join([f"{s:^15}" for s in header_symbols])
        print(header)
        print("-" * len(header))

        for state in sorted(list(self.states)):
            is_start = "->" if state == self.start_state else "  "
            is_final = "*" if state in self.final_states else " "
            row = f"{is_start}{is_final}{state:<12} |"
            
            for symbol in header_symbols:
                target = self.transitions.get(state, {}).get(symbol, "-")
                # Для NFA/ENFA выводим множество, для DFA - строку
                if isinstance(target, list):
                    target_str = "{" + ", ".join(sorted(target)) + "}" if target else "-"
                else:
                    target_str = target
                row += f"{target_str:^15}"
            print(row)
        print("-" * len(header))
        print("-> - начальное состояние, * - конечное состояние\n")
    
    @classmethod
    def from_json(cls, file_path):
        """Загружает автомат из JSON файла."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(data)
        return cls(**data)

class DFA(FiniteAutomaton):
    """Детерминированный конечный автомат."""
    def process_word(self, word, trace=False):
        current_state = self.start_state
        trace_log = []

        if trace:
            log_entry = f"Начало: состояние = {current_state}, слово = '{word}'"
            print(log_entry)
            trace_log.append(log_entry)

        for i, symbol in enumerate(word):
            if symbol not in self.alphabet:
                verdict = "Слово отвергнуто (символ не в алфавите)"
                if trace: print(verdict); trace_log.append(verdict)
                return False, trace_log

            # Если для состояния или символа нет перехода, слово отвергается
            next_state = self.transitions.get(current_state, {}).get(symbol)
            if next_state is None:
                verdict = f"Шаг {i+1}: Нет перехода из {current_state} по '{symbol}'. Слово отвергнуто."
                if trace: print(verdict); trace_log.append(verdict)
                return False, trace_log

            current_state = next_state
            if trace:
                log_entry = f"Шаг {i+1}: '{symbol}' -> {current_state:<10} | Осталось: '{word[i+1:]}'"
                print(log_entry)
                trace_log.append(log_entry)

        is_accepted = current_state in self.final_states
        verdict = f"\nИтог: Слово '{word}' {'принято' if is_accepted else 'отвергнуто'}. Конечное состояние: {current_state}"
        if trace: print(verdict); trace_log.append(verdict)
        return is_accepted, trace_log

class NFA(FiniteAutomaton):
    """Недетерминированный конечный автомат."""
    def process_word(self, word, trace=False):
        current_states = {self.start_state}
        trace_log = []

        if trace:
            log_entry = f"Начало: состояния = {sorted(list(current_states))}, слово = '{word}'"
            print(log_entry)
            trace_log.append(log_entry)

        for i, symbol in enumerate(word):
            if symbol not in self.alphabet:
                verdict = "Слово отвергнуто (символ не в алфавите)"
                if trace: print(verdict); trace_log.append(verdict)
                return False, trace_log

            next_states = set()
            for state in current_states:
                # Собираем все возможные переходы
                transitions_for_state = self.transitions.get(state, {}).get(symbol, [])
                next_states.update(transitions_for_state)
            
            current_states = next_states
            
            if not current_states:
                verdict = f"Шаг {i+1}: Нет доступных переходов по '{symbol}'. Слово отвергнуто."
                if trace: print(verdict); trace_log.append(verdict)
                return False, trace_log

            if trace:
                log_entry = f"Шаг {i+1}: '{symbol}' -> {sorted(list(current_states))!s:<25} | Осталось: '{word[i+1:]}'"
                print(log_entry)
                trace_log.append(log_entry)

        # Слово принято, если хотя бы одно из конечных состояний находится в множестве финальных
        is_accepted = not self.final_states.isdisjoint(current_states)
        verdict = f"\nИтог: Слово '{word}' {'принято' if is_accepted else 'отвергнуто'}. Конечные состояния: {sorted(list(current_states))}"
        if trace: print(verdict); trace_log.append(verdict)
        return is_accepted, trace_log

    def to_dfa(self):
        """Преобразует NFA в эквивалентный DFA."""
        print("\n--- Преобразование NFA в DFA ---")
        
        dfa_transitions = {}
        dfa_states = set()
        dfa_final_states = set()

        # Начальное состояние DFA - это множество, содержащее только начальное состояние NFA
        initial_dfa_state = frozenset([self.start_state])
        
        queue = deque([initial_dfa_state])
        processed_states = {initial_dfa_state}

        # Словарь для красивых имен состояний DFA (Q0, Q1, ...)
        state_names = {initial_dfa_state: "Q0"}
        next_state_idx = 1

        while queue:
            current_nfa_states_set = queue.popleft()
            dfa_state_name = state_names[current_nfa_states_set]
            dfa_states.add(dfa_state_name)

            # Проверяем, является ли текущее состояние DFA конечным
            if not self.final_states.isdisjoint(current_nfa_states_set):
                dfa_final_states.add(dfa_state_name)

            dfa_transitions[dfa_state_name] = {}

            for symbol in self.alphabet:
                next_nfa_states = set()
                for nfa_state in current_nfa_states_set:
                    next_nfa_states.update(self.transitions.get(nfa_state, {}).get(symbol, []))
                
                next_dfa_state = frozenset(next_nfa_states)

                if not next_dfa_state: # "мертвое" состояние
                    continue

                if next_dfa_state not in processed_states:
                    processed_states.add(next_dfa_state)
                    queue.append(next_dfa_state)
                    state_names[next_dfa_state] = f"Q{next_state_idx}"
                    next_state_idx += 1
                
                dfa_transitions[dfa_state_name][symbol] = state_names[next_dfa_state]
        
        print("Преобразование завершено.")
        return DFA(
            states=list(dfa_states),
            alphabet=list(self.alphabet),
            transitions=dfa_transitions,
            start_state="Q0",
            final_states=list(dfa_final_states)
        )

class ENFA(NFA):
    """Недетерминированный конечный автомат с эпсилон-переходами."""

    def epsilon_closure(self, states):
        """Вычисляет эпсилон-замыкание для множества состояний."""
        closure = set(states)
        stack = list(states)
        while stack:
            state = stack.pop()
            epsilon_moves = self.transitions.get(state, {}).get(EPSILON, [])
            for s in epsilon_moves:
                if s not in closure:
                    closure.add(s)
                    stack.append(s)
        return closure

    def process_word(self, word, trace=False):
        # Начальные состояния - эпсилон-замыкание стартового состояния
        current_states = self.epsilon_closure({self.start_state})
        trace_log = []

        if trace:
            log_entry = f"Начало: ε-замыкание({self.start_state}) = {sorted(list(current_states))!s:<20}, слово = '{word}'"
            print(log_entry)
            trace_log.append(log_entry)

        for i, symbol in enumerate(word):
            if symbol not in self.alphabet:
                verdict = "Слово отвергнуто (символ не в алфавите)"
                if trace: print(verdict); trace_log.append(verdict)
                return False, trace_log

            # 1. Переход по символу
            move_states = set()
            for state in current_states:
                move_states.update(self.transitions.get(state, {}).get(symbol, []))
            
            # 2. Эпсилон-замыкание результата
            current_states = self.epsilon_closure(move_states)

            if not current_states:
                verdict = f"Шаг {i+1}: Нет доступных переходов по '{symbol}' (с учетом ε). Слово отвергнуто."
                if trace: print(verdict); trace_log.append(verdict)
                return False, trace_log

            if trace:
                log_entry = (f"Шаг {i+1}: '{symbol}' -> move = {sorted(list(move_states))!s:<15} "
                             f"-> ε-замыкание = {sorted(list(current_states))!s:<20} | Осталось: '{word[i+1:]}'")
                print(log_entry)
                trace_log.append(log_entry)

        is_accepted = not self.final_states.isdisjoint(current_states)
        verdict = f"\nИтог: Слово '{word}' {'принято' if is_accepted else 'отвергнуто'}. Конечные состояния: {sorted(list(current_states))}"
        if trace: print(verdict); trace_log.append(verdict)
        return is_accepted, trace_log

    def to_nfa(self):
        """Преобразует ε-NFA в эквивалентный NFA без ε-переходов."""
        print("\n--- Преобразование ε-NFA в NFA ---")
        nfa_transitions = {}
        
        # Новые конечные состояния: все состояния, из которых можно достичь старого конечного состояния по ε-переходам
        new_final_states = set()
        for state in self.states:
            if not self.final_states.isdisjoint(self.epsilon_closure({state})):
                new_final_states.add(state)

        for state in self.states:
            nfa_transitions[state] = {}
            closure = self.epsilon_closure({state})
            for symbol in self.alphabet:
                move_states = set()
                for s_in_closure in closure:
                    move_states.update(self.transitions.get(s_in_closure, {}).get(symbol, []))
                
                # Итоговый переход - эпсилон-замыкание от результатов переходов по символу
                target_states = self.epsilon_closure(move_states)
                if target_states:
                    nfa_transitions[state][symbol] = sorted(list(target_states))

        print("Преобразование завершено.")
        return NFA(
            states=list(self.states),
            alphabet=list(self.alphabet),
            transitions=nfa_transitions,
            start_state=self.start_state,
            final_states=list(new_final_states)
        )

# --- Утилиты и главная функция ---

def load_automaton_from_file():
    """Запрашивает имя файла и тип автомата, загружает и возвращает объект."""
    while True:
        try:
            filename = input("Введите имя JSON файла (например, dfa.json): ")
            if not os.path.exists(filename):
                print(f"Файл '{filename}' не найден. Попробуйте снова.")
                continue

            automaton_type = input("Выберите тип автомата (1-DFA, 2-NFA, 3-ENFA): ")
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if automaton_type == '1':
                return DFA(**data)
            elif automaton_type == '2':
                return NFA(**data)
            elif automaton_type == '3':
                return ENFA(**data)
            else:
                print("Неверный тип. Попробуйте снова.")
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Ошибка при загрузке или проверке автомата: {e}")
            return None

def print_parallel_trace(log1, title1, log2, title2):
    """Выводит два лога трассировки параллельно."""
    max_len = max(len(log1), len(log2))
    log1.extend([""] * (max_len - len(log1)))
    log2.extend([""] * (max_len - len(log2)))
    
    width1 = max(len(s) for s in log1) if log1 else len(title1)
    width1 = max(width1, len(title1)) + 2

    print(f"\n{title1:<{width1}} | {title2}")
    print("-" * (width1 + 1) + "+" + "-" * (len(title2) + 2))
    
    for s1, s2 in zip(log1, log2):
        print(f"{s1:<{width1}} | {s2}")
    print()


def main():
    automaton = None
    converted_nfa = None
    converted_dfa = None

    while True:
        print("\n" + "="*40)
        print("      Меню работы с автоматами")
        print("="*40)
        print("1. Загрузить автомат из JSON")
        print("2. Показать таблицу переходов")
        print("3. Проверить слово (с трассировкой)")
        print("4. Преобразовать ε-NFA -> NFA")
        print("5. Преобразовать NFA -> DFA")
        print("6. Сравнить автоматы на одном слове")
        print("0. Выход")
        print("="*40)

        choice = input("Выберите действие: ")

        if choice == '1':
            automaton = load_automaton_from_file()
            converted_nfa = None # Сбрасываем преобразованные при загрузке нового
            converted_dfa = None
            if automaton:
                print(f"Автомат типа '{type(automaton).__name__}' успешно загружен.")

        elif choice == '2':
            if automaton:
                automaton.display_transition_table()
                if converted_nfa:
                    print("\n--- Преобразованный NFA ---")
                    converted_nfa.display_transition_table()
                if converted_dfa:
                    print("\n--- Преобразованный DFA ---")
                    converted_dfa.display_transition_table()
            else:
                print("Сначала загрузите автомат (пункт 1).")

        elif choice == '3':
            if automaton:
                word = input("Введите слово для проверки: ")
                automaton.process_word(word, trace=True)
            else:
                print("Сначала загрузите автомат (пункт 1).")

        elif choice == '4':
            if isinstance(automaton, ENFA):
                converted_nfa = automaton.to_nfa()
                print("ε-NFA успешно преобразован в NFA. Вы можете посмотреть таблицу (2) или сравнить работу (6).")
            else:
                print("Эта операция применима только к ε-NFA. Загрузите соответствующий автомат.")
        
        elif choice == '5':
            source_nfa = converted_nfa if converted_nfa else automaton
            if isinstance(source_nfa, NFA):
                 converted_dfa = source_nfa.to_dfa()
                 print("NFA успешно преобразован в DFA. Вы можете посмотреть таблицу (2) или сравнить работу (6).")
            else:
                print("Эта операция применима к NFA или к автомату, преобразованному из ε-NFA. Загрузите NFA или сначала выполните пункт 4.")

        elif choice == '6':
            if not automaton:
                print("Сначала загрузите автомат (пункт 1).")
                continue
            
            target_automaton = None
            if converted_dfa:
                target_automaton = converted_dfa
                original_automaton = converted_nfa if converted_nfa else automaton
                title1, title2 = f"Трассировка ({type(original_automaton).__name__})", "Трассировка (DFA)"
            elif converted_nfa:
                target_automaton = converted_nfa
                original_automaton = automaton
                title1, title2 = "Трассировка (ε-NFA)", "Трассировка (NFA)"
            else:
                print("Сначала нужно преобразовать автомат (пункты 4 или 5).")
                continue
                
            word = input("Введите слово для сравнения: ")
            _, log1 = original_automaton.process_word(word, trace=False)
            _, log2 = target_automaton.process_word(word, trace=False)
            print_parallel_trace(log1, title1, log2, title2)

        elif choice == '0':
            print("Завершение работы.")
            break
        else:
            print("Неверный ввод, попробуйте снова.")

if __name__ == "__main__":
    main()
