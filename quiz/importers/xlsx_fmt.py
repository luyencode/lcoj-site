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
    'answer_display',
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
    'Answer Display',
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
    'Answer Display': (
        'SA only — human-readable answer shown to students on the result page.\n'
        'Leave blank to fall back to showing the raw regex patterns.\n'
        'Example: if patterns are  (?i)paris , write  Paris  here.'
    ),
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
    'X': 28,                          # answer_display
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
            explanation, 'Yes' if shuffle else None, None, None]
    return tuple(row)


def _ma(code, title, content, choices_expls, correct_csv, points,
        category, level, explanation, strategy='Partial credit'):
    row = [code, 'Multiple Answer', title, content]
    for i in range(MAX_CHOICES):
        if i < len(choices_expls):
            row += list(choices_expls[i])
        else:
            row += [None, None]
    row += [correct_csv, points, category, level, explanation, 'Yes', strategy, None]
    return tuple(row)


def _tf(code, title, content, correct_bool, points, category, level, explanation):
    row = [code, 'True/False', title, content] + [None] * (MAX_CHOICES * 2)
    row += ['True' if correct_bool else 'False', points, category,
            level, explanation, None, None, None]
    return tuple(row)


def _sa(code, title, content, patterns, points, category, level, explanation,
        answer_display=''):
    row = [code, 'Short Answer', title, content] + [None] * (MAX_CHOICES * 2)
    row += [' | '.join(patterns), points, category, level,
            explanation, None, None, answer_display or None]
    return tuple(row)


# ── Example questions (diverse topics) ───────────────────────────────────────

EXAMPLE_ROWS = (
    # ── Multiple Choice ───────────────────────────────────────────────────────
    _mc(
        code='pylistlen',
        title='Python – list length',
        content='What is the output of `len([1, 2, 3, 4, 5])`?',
        choices_expls=[
            ('3', 'Incorrect — 3 is the length of [1, 2, 3], not a 5-element list.'),
            ('4', 'Incorrect — off by one; the list contains 5 elements.'),
            ('5', '✓ `len()` returns the number of items in the list, which is 5.'),
            ('6', 'Incorrect — there is no hidden element; the list has exactly 5 items.'),
        ],
        correct_1based=3, points=1, category='Python Basics', level='Easy',
        explanation='`len(sequence)` returns the number of items. `[1, 2, 3, 4, 5]` has 5 items, so the answer is **5**.',
        shuffle=True,
    ),

    _mc(
        code='pystrmethod',
        title='Python – uppercase method',
        content='Which method converts a string to **all uppercase** letters?',
        choices_expls=[
            ('str.lower()', 'Incorrect — `lower()` converts to all lowercase.'),
            ('str.capitalize()', 'Incorrect — `capitalize()` only uppercases the first character.'),
            ('str.title()', 'Incorrect — `title()` uppercases the first letter of each word.'),
            ('str.upper()', '✓ `upper()` returns a copy of the string with all characters converted to uppercase.'),
        ],
        correct_1based=4, points=1, category='Python Basics', level='Easy',
        explanation='`str.upper()` returns a new string with every character converted to its uppercase equivalent, e.g. `"hello".upper()` → `"HELLO"`.',
        shuffle=True,
    ),

    _mc(
        code='pydictget',
        title='Python – dict.get() with default',
        content='Given `d = {"a": 1, "b": 2}`, what does `d.get("c", 99)` return?',
        choices_expls=[
            ('None', 'Incorrect — `None` is returned by `d.get("c")` with no default, but a default of 99 is provided here.'),
            ('KeyError', 'Incorrect — `dict.get()` never raises `KeyError`; that is its purpose.'),
            ('99', '✓ When the key is absent, `get()` returns the supplied default value, which is 99.'),
            ('0', 'Incorrect — 0 is not the default; the caller explicitly passed 99.'),
        ],
        correct_1based=3, points=1, category='Python Basics', level='Easy',
        explanation='`dict.get(key, default)` returns `default` (here `99`) when `key` is not found, instead of raising a `KeyError`.',
        shuffle=True,
    ),

    _mc(
        code='mathtrianglearea',
        title='Math – area of a triangle',
        content='What is the area of a triangle with **base = 8** and **height = 5**?',
        choices_expls=[
            ('13', 'Incorrect — 13 = 8 + 5; you added instead of using the area formula.'),
            ('40', 'Incorrect — 40 = 8 × 5; you forgot to multiply by ½.'),
            ('20', '✓ Area = ½ × base × height = ½ × 8 × 5 = **20**.'),
            ('80', 'Incorrect — 80 = 2 × 8 × 5; the factor should be ½, not 2.'),
        ],
        correct_1based=3, points=1, category='Mathematics', level='Easy',
        explanation='The area of a triangle is **½ × base × height**. Here: ½ × 8 × 5 = **20** square units.',
        shuffle=True,
    ),

    _mc(
        code='httpnotfound',
        title='HTTP – 404 status code',
        content='Which HTTP status code indicates that the requested resource was **not found** on the server?',
        choices_expls=[
            ('200', 'Incorrect — 200 OK means the request succeeded.'),
            ('301', 'Incorrect — 301 Moved Permanently is a redirect status.'),
            ('403', 'Incorrect — 403 Forbidden means the server refused to authorize the request.'),
            ('404', '✓ 404 Not Found means the server could not locate the requested resource.'),
        ],
        correct_1based=4, points=1, category='Web / HTTP', level='Easy',
        explanation='**404 Not Found** is returned when the server cannot find the resource matching the URL.',
        shuffle=False,
    ),

    # ── Multiple Answer ───────────────────────────────────────────────────────
    _ma(
        code='pymutabletypes',
        title='Python – mutable built-in types',
        content='Which of the following Python built-in types are **mutable**? Select all that apply.',
        choices_expls=[
            ('list', '✓ Lists are mutable — elements can be added, removed, or changed in place.'),
            ('tuple', 'Incorrect — tuples are immutable; their contents cannot be changed after creation.'),
            ('dict', '✓ Dictionaries are mutable — key-value pairs can be added, updated, or deleted.'),
            ('str', 'Incorrect — strings are immutable; operations return new string objects.'),
            ('set', '✓ Sets are mutable — elements can be added or removed (unlike `frozenset`).'),
        ],
        correct_csv='1,3,5', points=2, category='Python Basics', level='Medium',
        explanation='**Mutable** types can be modified after creation: `list`, `dict`, and `set`. **Immutable** types cannot: `tuple`, `str`, `int`, `float`, `frozenset`.',
        strategy='Partial credit',
    ),

    _ma(
        code='httpsafemethods',
        title='HTTP – safe request methods',
        content='Which of the following HTTP methods are **safe** (i.e. they must not modify server state)? Select all that apply.',
        choices_expls=[
            ('GET', '✓ GET retrieves a resource without modifying it.'),
            ('POST', 'Incorrect — POST submits data that typically creates or modifies a resource.'),
            ('HEAD', '✓ HEAD is identical to GET but returns only headers; no state change.'),
            ('PUT', 'Incorrect — PUT replaces a resource and modifies server state.'),
            ('OPTIONS', '✓ OPTIONS describes communication options without modifying state.'),
            ('DELETE', 'Incorrect — DELETE removes a resource and is not safe.'),
        ],
        correct_csv='1,3,5', points=2, category='Web / HTTP', level='Medium',
        explanation='RFC 9110 defines **safe methods** as read-only: **GET**, **HEAD**, and **OPTIONS**. POST, PUT, PATCH, and DELETE modify state.',
        strategy='All or nothing',
    ),

    # ── True / False ──────────────────────────────────────────────────────────
    _tf(
        code='tfpythonzeroindex',
        title='Python – zero-based indexing',
        content='In Python, the **first element** of a list is accessed with index `1`.',
        correct_bool=False, points=1, category='Python Basics', level='Easy',
        explanation='**False.** Python uses **zero-based indexing**. The first element is at index `0`, not `1`.',
    ),

    _tf(
        code='tfprimeevenexist',
        title='Math – even prime number',
        content='There exists an **even** prime number.',
        correct_bool=True, points=1, category='Mathematics', level='Easy',
        explanation='**True.** The number **2** is the only even prime number. Every other even number is divisible by 2 and is therefore composite.',
    ),

    _tf(
        code='tfaustraliacapital',
        title='Geography – Australia\'s capital',
        content='**Sydney** is the capital city of Australia.',
        correct_bool=False, points=1, category='Geography', level='Easy',
        explanation='**False.** The capital of Australia is **Canberra**, a purpose-built city chosen as a compromise between Sydney and Melbourne.',
    ),

    # ── Short Answer ──────────────────────────────────────────────────────────
    _sa(
        code='safrancecapital',
        title='Geography – capital of France',
        content='What is the capital city of **France**?',
        patterns=[r'(?i)paris'],
        points=1, category='Geography', level='Easy',
        explanation='**Paris** has been the capital of France since the late 10th century.',
        answer_display='Paris',
    ),

    _sa(
        code='sapythonlenbuiltin',
        title='Python – length function name',
        content='What built-in **function** returns the number of items in a Python list or string?\n'
                '(type just the function name, with or without parentheses)',
        patterns=[r'(?i)len\s*\(\s*\)', r'(?i)len'],
        points=1, category='Python Basics', level='Easy',
        explanation='`len()` is the built-in function for sequence length. It works on lists, strings, tuples, dicts, and any iterable.',
        answer_display='len  (or  len())',
    ),

    _sa(
        code='samathsqrt144',
        title='Math – square root of 144',
        content='What is the **square root** of 144?',
        patterns=[r'12', r'(?i)twelve'],
        points=1, category='Mathematics', level='Easy',
        explanation='√144 = **12**, because 12 × 12 = 144.',
        answer_display='12',
    ),

    _sa(
        code='sahttp200meaning',
        title='HTTP – reason phrase for 200',
        content='What is the standard **reason phrase** for HTTP status code `200`?\n'
                '(e.g. 404 → Not Found)',
        patterns=[r'(?i)ok', r'(?i)200\s*ok'],
        points=1, category='Web / HTTP', level='Easy',
        explanation='HTTP **200 OK** is the standard response for a successful request.',
        answer_display='OK',
    ),
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
        q.answer_display = str(data.get('answer_display') or '').strip()
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
            getattr(q, 'answer_display', None) if q.type == grading.SA else None,
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
