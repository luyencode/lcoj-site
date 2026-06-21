# Quiz Clone Feature — Design Spec

**Date:** 2026-06-21  
**Status:** Approved

## Overview

Allow quiz editors to clone an existing quiz into a new draft. The clone copies all quiz metadata and question links (shallow — same `QuizQuestion` bank objects, new `QuizQuestionLink` rows). The clone is created immediately with an auto-generated code and the editor is redirected to its edit page.

---

## 1. Model method — `Quiz.clone(author)`

Location: `quiz/models.py`, added to the `Quiz` class.

```python
def clone(self, author: Profile) -> 'Quiz':
```

Runs inside a single atomic transaction. Steps:

1. **Generate unique code.** Try `{original_code}2`, `{original_code}3`, … `{original_code}9` — pick the first code not yet in the DB. Cap at 9 attempts; if all are taken, raise a `ValueError` (caller surfaces this as an error message).
2. **Copy scalar fields:** `description`, `time_limit`, `max_attempts`, `shuffle_questions`, `result_feedback`, `integrity_monitoring`, `is_organization_private`.
3. **Set derived fields:**
   - `name` = `"Copy of {original_name}"`
   - `code` = generated code from step 1
   - `is_public` = `False`
   - `start_time` = `None`
   - `end_time` = `None`
4. **Save** the new `Quiz` instance.
5. **Copy M2M relationships:**
   - `organizations` — copied as-is.
   - `curators` — copied as-is.
   - `testers` — copied as-is.
   - `authors` — set to `[author]` only (the cloner becomes sole author).
6. **Copy question links.** For each `QuizQuestionLink` on the original quiz, create a new `QuizQuestionLink` on the clone with the same `question`, `points`, and `order`.
7. Return the new `Quiz` instance.

---

## 2. View & URL

### View

`QuizClone` in `quiz/views/editor.py`. Uses the existing `QuizEditorObjectMixin` which resolves `self.quiz` by code and enforces object-level edit permission.

```python
class QuizClone(QuizEditorObjectMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            clone = self.quiz.clone(request.profile)
        except ValueError:
            messages.error(request, _('Could not generate a unique code for the clone. Rename the original quiz first.'))
            return redirect('quiz_edit', quiz=self.quiz.code)
        messages.success(request, _('Quiz cloned. Update the name and settings before publishing.'))
        return redirect('quiz_edit', quiz=clone.code)
```

Only `POST` is handled — `GET` returns 405.

### URL

Added to `quiz/urls.py` inside the `/<str:quiz>` group:

```python
path('/clone', editor.QuizClone.as_view(), name='quiz_clone'),
```

---

## 3. UI entry points

Both use a plain `<form method="post">` with a CSRF token — no JavaScript required.

### Quiz edit page (`quiz/quiz_form.html`)

A **Clone** button in the action bar, shown only when `editing=True` (i.e. existing quiz, not the "New Quiz" form). Placed alongside the Save button.

### Quiz detail page (`quiz/quiz_detail.html`)

A **Clone** button shown only when `request.user.is_authenticated and quiz.is_editable_by(request.user)`. Positioned in the editor action area.

---

## 4. Error handling

| Scenario | Behaviour |
|---|---|
| All 8 suffix codes (`{code}2`–`{code}9`) are taken | `messages.error`, redirect back to original quiz edit page |
| Non-editor hits `/clone` | `QuizEditorObjectMixin` raises `Http404` |
| GET request to `/clone` | 405 Method Not Allowed |

---

## 5. Tests

New file `quiz/tests/test_clone.py` (or added to `test_models.py`):

| Test | What it verifies |
|---|---|
| `test_clone_copies_fields` | Scalar fields copied, `is_public=False`, `start_time=None`, `end_time=None` |
| `test_clone_name_prefixed` | Clone `name` starts with `"Copy of "` |
| `test_clone_copies_question_links` | New `QuizQuestionLink` rows exist with correct `question`, `points`, `order` |
| `test_clone_question_links_are_shallow` | Link points to same `QuizQuestion` pk, not a new one |
| `test_clone_author_is_cloner` | `clone.authors.all()` contains only the cloning profile |
| `test_clone_copies_m2m` | `organizations`, `curators`, `testers` are copied |
| `test_clone_code_generation` | When `{code}2` is free, clone gets `{code}2` |
| `test_clone_code_generation_collision` | When `{code}2`–`{code}4` are taken, clone gets `{code}5` |
| `test_clone_code_generation_exhausted` | All suffixes taken → `ValueError` raised |
| `test_clone_view_post_redirects` | Editor POST → 302 to clone edit page |
| `test_clone_view_non_editor_404` | Non-editor POST → 404 |

---

## 6. Out of scope (v1)

- Deep-copying `QuizQuestion` objects (questions remain shared bank items).
- Custom code/name input before cloning (clone-then-edit workflow chosen).
- Cloning individual questions in the question bank.
