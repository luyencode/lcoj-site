"""XLSX import/export with friendly column names, dropdowns and separate SA regex column."""
import io

from quiz import grading
from quiz.importers.base import (ParsedQuestion, correct_to_spec,
                                 parse_correct_spec, validate_question)

MAX_CHOICES = 6

# ── Display ↔ internal code mappings ──────────────────────────────────────────

TYPE_DISPLAY = {
    grading.MC: 'Multiple Choice',
    grading.MA: 'Multiple Answer',
    grading.TF: 'True/False',
    grading.SA: 'Short Answer',
}
_TYPE_PARSE = {}
for _code, _label in TYPE_DISPLAY.items():
    _TYPE_PARSE[_label.lower()] = _code
    _TYPE_PARSE[_code.lower()] = _code   # also accept old abbreviations

LEVEL_DISPLAY = {'easy': 'Easy', 'medium': 'Medium', 'hard': 'Hard'}
_LEVEL_PARSE = {v.lower(): k for k, v in LEVEL_DISPLAY.items()}
_LEVEL_PARSE.update({k: k for k in LEVEL_DISPLAY})  # accept lowercase too

MA_STRATEGY_DISPLAY = {
    grading.MA_ALL_OR_NOTHING:    'All or nothing',
    grading.MA_PARTIAL_CREDIT:    'Partial credit',
    grading.MA_RIGHT_MINUS_WRONG: 'Right minus wrong',
    grading.MA_CORRECT_ONLY:      'Correct only',
}
_MA_STRATEGY_PARSE = {v.lower(): k for k, v in MA_STRATEGY_DISPLAY.items()}
_MA_STRATEGY_PARSE.update({k: k for k in MA_STRATEGY_DISPLAY})

TRUTHY = ('yes', 'true', '1', 'x', 'có')

# ── Column layout ─────────────────────────────────────────────────────────────

# Internal keys (used for parsing)
# Interleaved: choice_N then choice_explanation_N
HEADERS = (
    'code',
    'type', 'title', 'content',
    'choice_1', 'choice_explanation_1',
    'choice_2', 'choice_explanation_2',
    'choice_3', 'choice_explanation_3',
    'choice_4', 'choice_explanation_4',
    'choice_5', 'choice_explanation_5',
    'choice_6', 'choice_explanation_6',
    'correct',
    'points', 'category', 'level',
    'explanation', 'shuffle', 'ma_strategy',
)

# Human-readable labels shown in row 1
HEADER_LABELS = (
    'Code',
    'Type', 'Title', 'Question',
    'Choice 1', 'Explanation 1',
    'Choice 2', 'Explanation 2',
    'Choice 3', 'Explanation 3',
    'Choice 4', 'Explanation 4',
    'Choice 5', 'Explanation 5',
    'Choice 6', 'Explanation 6',
    'Correct Answer',
    'Points', 'Category', 'Level',
    'Explanation', 'Shuffle Choices', 'MA Strategy',
)

# Pre-compute column letters (A=0, B=1, ...)
def _col_letter(header_key):
    return chr(ord('A') + HEADERS.index(header_key))


HEADER_NOTES = {
    'Code': (
        'Unique short identifier for this question — lowercase letters and '
        'digits only, no spaces or underscores. Examples: py101q1, tfindent3'
    ),
    'Type': (
        'Question type — choose from the dropdown:\n'
        '  Multiple Choice  : single correct choice\n'
        '  Multiple Answer  : one or more correct choices\n'
        '  True/False       : boolean statement\n'
        '  Short Answer     : student types a text answer'
    ),
    'Correct Answer': (
        'MC  : choice number, e.g.  2\n'
        'MA  : comma-separated numbers, e.g.  1,3\n'
        'TF  : True  or  False\n'
        'SA  : regex patterns separated by  |  (each is tested with re.fullmatch)\n'
        '      Use (?i) prefix for case-insensitive:  (?i)python\n'
        '      Use | to offer alternatives:  3|three\n'
        '      Example:  (?i)def  |  (?i)define\n'
        '      Digits: \\d+   Any word: \\w+'
    ),
    'MA Strategy': (
        'How Multiple Answer questions are scored — choose from dropdown:\n'
        '  All or nothing    : full score only if every correct choice selected\n'
        '  Partial credit    : proportional score minus wrong-answer penalty\n'
        '  Right minus wrong : (correct − wrong) / total_correct\n'
        '  Correct only      : correct / total_correct, no wrong-answer penalty'
    ),
    'Shuffle Choices': 'Yes — randomise the choice order shown to each student.',
    'Level': 'Difficulty — choose from dropdown: Easy, Medium, Hard',
    'Explanation 1': 'Optional explanation for choice 1, shown to students after submitting.',
    'Explanation 2': 'Optional explanation for choice 2, shown to students after submitting.',
    'Explanation 3': 'Optional explanation for choice 3, shown to students after submitting.',
    'Explanation 4': 'Optional explanation for choice 4, shown to students after submitting.',
    'Explanation 5': 'Optional explanation for choice 5, shown to students after submitting.',
    'Explanation 6': 'Optional explanation for choice 6, shown to students after submitting.',
}

# 23 columns: A through W
COL_WIDTHS = {
    'A': 16,                          # code
    'B': 18,  'C': 28,  'D': 46,     # type, title, content
    'E': 22,  'F': 32,               # choice_1, explanation_1
    'G': 22,  'H': 32,               # choice_2, explanation_2
    'I': 22,  'J': 32,               # choice_3, explanation_3
    'K': 22,  'L': 32,               # choice_4, explanation_4
    'M': 22,  'N': 32,               # choice_5, explanation_5
    'O': 22,  'P': 32,               # choice_6, explanation_6
    'Q': 32,                          # correct
    'R': 8,   'S': 18,  'T': 12,    # points, category, level
    'U': 40,  'V': 14,  'W': 18,    # explanation, shuffle, ma_strategy
}

# ── Row helper: each row is exactly 22 values matching HEADERS ────────────────
# col order: type, title, content,
#            ch1, ex1, ch2, ex2, ch3, ex3, ch4, ex4, ch5, ex5, ch6, ex6,
#            correct, points, category, level, explanation, shuffle, ma_strategy

def _mc(code, title, content, choices_expls, correct_1based, points,
        category, level, explanation, shuffle=False):
    """choices_expls: list of (text, explanation) tuples."""
    row = [code, 'Multiple Choice', title, content]
    for i in range(MAX_CHOICES):
        if i < len(choices_expls):
            row += list(choices_expls[i])
        else:
            row += [None, None]
    row += [str(correct_1based), points, category, level,
            explanation, 'Yes' if shuffle else None, None]
    return tuple(row)


def _ma(code, title, content, choices_expls, correct_csv, points,
        category, level, explanation, strategy='Partial credit'):
    row = [code, 'Multiple Answer', title, content]
    for i in range(MAX_CHOICES):
        if i < len(choices_expls):
            row += list(choices_expls[i])
        else:
            row += [None, None]
    row += [correct_csv, points, category, level, explanation, 'Yes', strategy]
    return tuple(row)


def _tf(code, title, content, correct_bool, points, category, level, explanation):
    row = [code, 'True/False', title, content] + [None] * (MAX_CHOICES * 2)
    row += ['True' if correct_bool else 'False', points, category,
            level, explanation, None, None]
    return tuple(row)


def _sa(code, title, content, patterns, points, category, level, explanation):
    row = [code, 'Short Answer', title, content] + [None] * (MAX_CHOICES * 2)
    row += [' | '.join(patterns), points, category, level,
            explanation, None, None]
    return tuple(row)


# ── Python programming questions ──────────────────────────────────────────────

EXAMPLE_ROWS = (
    # ── Multiple Choice ───────────────────────────────────────────────────────
    _mc('pylistlen',
        'list len()',
        'What does len([10, 20, 30]) return?',
        [('1', '1 is just the first element — len() counts elements, not values.'),
         ('2', '2 would be correct for a 2-element list.'),
         ('3', '✓ Correct! len() returns the number of elements in the list.'),
         ('4', '4 would require a 4-element list.')],
        3, 1, 'Python Basics', 'Easy',
        'len() is a built-in that returns the number of items in any sequence.',
        shuffle=True),

    _mc('pyfloordiv',
        'Floor division',
        'What is the result of 7 // 2 in Python?',
        [('3',   '✓ Correct! // performs integer (floor) division, discarding the decimal.'),
         ('3.5', '3.5 is regular division: use 7 / 2 for that.'),
         ('1',   '1 is the remainder: that would be 7 % 2.'),
         ('4',   'Floor division rounds down, not up.')],
        1, 1, 'Python Basics', 'Easy',
        '// discards the fractional part. 7 // 2 = 3 (not 3.5).'),

    _mc('pyfunckey',
        'Function keyword',
        'Which keyword is used to define a function in Python?',
        [('function', 'This is JavaScript syntax — not valid in Python.'),
         ('def',      '✓ Correct! def is the Python keyword for defining functions.'),
         ('func',     'Not a Python keyword.'),
         ('define',   'Not a Python keyword.')],
        2, 1, 'Python Basics', 'Easy',
        'Syntax: def function_name(parameters): — the colon and indented body are required.',
        shuffle=True),

    _mc('pytypeof',
        'type() output',
        'What does print(type([])) output?',
        [("<class 'list'>",  "✓ Correct! Python 3 shows <class 'typename'> for all types."),
         ('list',            'Just the word — Python includes the full <class ...> wrapper.'),
         ("<type 'list'>",   "This was Python 2 syntax."),
         ("<class 'array'>", "[] creates a list, not an array.")],
        1, 1, 'Python Basics', 'Medium',
        "type() returns the type object. In Python 3 it prints as <class 'list'>.",
        shuffle=True),

    _mc('pystrslice',
        'String slicing',
        'What does "Python"[1:4] return?',
        [('Pyt',  'That would be "Python"[:3] — slicing from 0.'),
         ('yth',  '✓ Correct! Index 1 to 3 (4 is exclusive): y-t-h.'),
         ('ytho', 'Index 1 to 4 exclusive means only up to index 3.'),
         ('hon',  'That would be "Python"[3:6] or "Python"[-3:].')],
        2, 1, 'Python Strings', 'Medium',
        'Slicing s[start:end] returns characters from start up to (not including) end.',
        shuffle=True),

    # ── Multiple Answer ───────────────────────────────────────────────────────
    _ma('pymutable',
        'Mutable types',
        'Which Python types are MUTABLE? (select all)',
        [('list',  'Mutable — elements can be added, removed, or changed.'),
         ('tuple', 'Immutable — once created, a tuple cannot be changed.'),
         ('dict',  'Mutable — key-value pairs can be added, removed, or updated.'),
         ('str',   'Immutable — operations on strings always create a new string.'),
         ('set',   'Mutable — elements can be added or removed.')],
        '1,3,5', 2, 'Python Data Types', 'Medium',
        'Mutable: list, dict, set, bytearray. Immutable: int, float, str, tuple, frozenset.',
        strategy='Partial credit'),

    _ma('pylistmeth',
        'Valid list methods',
        'Which are valid methods on a Python list? (select all)',
        [('.append(x)', 'Valid — adds x to the end of the list.'),
         ('.sort()',     'Valid — sorts the list in-place (modifies the original).'),
         ('.push(x)',    'Not a list method! Python uses .append() — push() is from JavaScript.'),
         ('.index(x)',   'Valid — returns the index of the first occurrence of x.'),
         ('.pop()',      'Valid — removes and returns the last element (or at a given index).')],
        '1,2,4,5', 2, 'Python Data Types', 'Medium',
        'Python list methods: append, extend, insert, remove, pop, index, count, sort, reverse, copy.',
        strategy='All or nothing'),

    # ── True/False ────────────────────────────────────────────────────────────
    _tf('pyindent',
        'Indentation blocks',
        'Python uses curly braces {} to define code blocks (like if statements and functions).',
        False, 1, 'Python Basics', 'Easy',
        'Python uses indentation (whitespace) for blocks — no curly braces needed. '
        'This is enforced by the language.'),

    _tf('pyzerofalse',
        '0 == False',
        'In Python, the expression  0 == False  evaluates to True.',
        True, 1, 'Python Basics', 'Medium',
        'Python booleans are a subclass of int. True == 1 and False == 0, '
        'so 0 == False is True.'),

    _tf('pystrimm',
        'String immutability',
        'In Python, you can change a character in a string by writing  s[0] = "X".',
        False, 1, 'Python Strings', 'Easy',
        'Strings are immutable — s[0] = "X" raises a TypeError. '
        'To modify, build a new string: s = "X" + s[1:].'),

    # ── Short Answer ──────────────────────────────────────────────────────────
    _sa('pylenname',
        'len() function name',
        'What is the name of the built-in function that returns the number of items in a list?\n'
        '(type just the function name, with or without parentheses)',
        [r'(?i)len\(?\)?'],
        1, 'Python Basics', 'Easy',
        'len(sequence) works on lists, strings, tuples, dicts, sets, and any iterable.'),

    _sa('pyintdivop',
        'Integer division operator',
        'What operator performs integer (floor) division in Python? (e.g.  7 ___ 2 = 3)',
        [r'//'],
        1, 'Python Basics', 'Easy',
        '// discards the decimal: 7 // 2 = 3. For remainder use %, for exact division use /.'),

    _sa('pyupper',
        'Output of upper()',
        'What is the output of:  "hello".upper()',
        [r'HELLO', r"'HELLO'"],
        1, 'Python Strings', 'Easy',
        '.upper() returns a new string with all characters converted to uppercase.'),

    _sa('pyrangeres',
        'Range result',
        'What is the value of  list(range(3))  in Python?\n'
        '(write the exact Python list representation)',
        [r'\[0, 1, 2\]', r'\[0,1,2\]'],
        1, 'Python Basics', 'Easy',
        'range(n) generates integers 0 through n-1. list(range(3)) = [0, 1, 2].'),
)


# ── SA helper ────────────────────────────────────────────────────────────────

def _sa_correct_to_cell(correct_answers):
    """SA correct_answers (list of regex strings or legacy dicts) → cell string."""
    parts = []
    for a in (correct_answers or []):
        parts.append(a.get('text', '') if isinstance(a, dict) else str(a))
    return ' | '.join(parts) or None


# ── Public API ────────────────────────────────────────────────────────────────

def parse(file_obj):
    """file-like → list[ParsedQuestion]."""
    from openpyxl import load_workbook
    try:
        sheet = load_workbook(file_obj, read_only=True,
                              data_only=True).active
    except Exception as exc:
        broken = ParsedQuestion(row=0)
        broken.errors.append('Cannot read XLSX file: %s' % exc)
        return [broken]

    questions = []
    for row_num, cells in enumerate(
            sheet.iter_rows(min_row=2, values_only=True), start=2):
        cells = list(cells) + [None] * (len(HEADERS) - len(cells))
        if all(c in (None, '') for c in cells):
            continue
        data = dict(zip(HEADERS, cells))
        q = ParsedQuestion(row=row_num)
        questions.append(q)

        q.code = str(data.get('code') or '').strip().lower()
        raw_type = str(data['type'] or '').strip()
        q.type = _TYPE_PARSE.get(raw_type.lower(), raw_type.upper())

        q.title = str(data['title'] or '').strip()
        q.content = str(data['content'] or '')
        raw_choices = [
            str(data['choice_%d' % i]).strip()
            for i in range(1, MAX_CHOICES + 1)
            if data['choice_%d' % i] not in (None, '')
        ]
        all_explanations = [
            str(data.get('choice_explanation_%d' % i) or '').strip()
            for i in range(1, MAX_CHOICES + 1)
        ]
        all_explanations = all_explanations[:len(raw_choices)]
        q.choices = [
            {'text': text, 'explanation': expl}
            for text, expl in zip(raw_choices, all_explanations)
        ]

        q.points = data['points'] if data['points'] is not None else 1.0

        q.category = str(data['category'] or '').strip()

        raw_level = str(data['level'] or 'easy').strip()
        q.level = _LEVEL_PARSE.get(raw_level.lower(), raw_level.lower())

        q.explanation = str(data['explanation'] or '')
        q.shuffle = str(data['shuffle'] or '').strip().lower() in TRUTHY

        raw_strategy = str(data['ma_strategy'] or '').strip()
        q.ma_strategy = _MA_STRATEGY_PARSE.get(
            raw_strategy.lower(), raw_strategy or grading.MA_ALL_OR_NOTHING)

        if q.type in (grading.MC, grading.MA, grading.TF, grading.SA):
            q.correct, errs = parse_correct_spec(
                q.type, data['correct'], len(q.choices))
            q.errors.extend(errs)

        validate_question(q)
    return questions


def write(questions):
    """list[ParsedQuestion] → BytesIO of an importable workbook."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = 'Questions'
    _style_sheet(ws)
    ws.append(list(HEADER_LABELS))
    _apply_header_style(ws)

    for q in questions:
        correct_text = (_sa_correct_to_cell(q.correct)
                        if q.type == grading.SA
                        else correct_to_spec(q.type, q.correct))
        raw_choices = q.choices or []
        if raw_choices and isinstance(raw_choices[0], dict):
            choice_texts = [c.get('text', '') for c in raw_choices]
            expls = [c.get('explanation', '') or None for c in raw_choices]
        else:
            choice_texts = [str(c) for c in raw_choices]
            expls = [None] * len(choice_texts)
        choices = choice_texts + [None] * (MAX_CHOICES - len(choice_texts))
        expls = expls + [None] * (MAX_CHOICES - len(expls))
        interleaved = []
        for i in range(MAX_CHOICES):
            interleaved += [choices[i] or None, expls[i] or None]
        ws.append([
            q.code,
            TYPE_DISPLAY.get(q.type, q.type), q.title, q.content,
            *interleaved,
            correct_text,
            q.points, q.category, LEVEL_DISPLAY.get(q.level, q.level),
            q.explanation, 'Yes' if q.shuffle else None,
            MA_STRATEGY_DISPLAY.get(q.ma_strategy, None) if q.type == grading.MA else None,
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def template():
    """Downloadable starter workbook with example rows and Excel dropdowns."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = 'Questions'
    _style_sheet(ws)
    ws.append(list(HEADER_LABELS))
    _apply_header_style(ws)
    for row in EXAMPLE_ROWS:
        ws.append(list(row))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ── Styling helpers ───────────────────────────────────────────────────────────

def _style_sheet(ws):
    """Column widths, freeze pane, wrap text, and dropdown validations."""
    from openpyxl.worksheet.datavalidation import DataValidation

    for col_letter, width in COL_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width

    ws.freeze_panes = 'A2'

    END = 1001

    def _add_dv(formula, col):
        dv = DataValidation(
            type='list', formula1=formula,
            allow_blank=True, showDropDown=False,
            showErrorMessage=True,
        )
        ws.add_data_validation(dv)
        dv.sqref = f'{col}2:{col}{END}'

    _add_dv(f'"{",".join(TYPE_DISPLAY.values())}"',        _col_letter('type'))
    _add_dv(f'"{",".join(LEVEL_DISPLAY.values())}"',       _col_letter('level'))
    _add_dv('"Yes,No"',                                    _col_letter('shuffle'))
    _add_dv(f'"{",".join(MA_STRATEGY_DISPLAY.values())}"', _col_letter('ma_strategy'))


def _apply_header_style(ws):
    """Bold + dark green header row with explanatory cell notes."""
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill

    hdr_font  = Font(bold=True, color='FFFFFF', size=11)
    hdr_fill  = PatternFill(start_color='1B5E20', end_color='1B5E20',
                            fill_type='solid')
    hdr_align = Alignment(horizontal='center', vertical='center',
                          wrap_text=True)

    for col_idx, label in enumerate(HEADER_LABELS, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = label
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = hdr_align
        if label in HEADER_NOTES:
            cell.comment = Comment(HEADER_NOTES[label], 'Quiz Import')

    ws.row_dimensions[1].height = 30
