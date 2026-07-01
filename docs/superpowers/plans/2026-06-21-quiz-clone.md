# Quiz Clone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let quiz editors clone an existing quiz into a private draft with one click, preserving all metadata and question links (shallow).

**Architecture:** A `Quiz.clone(author)` model method does all the work in one atomic transaction; a `QuizClone` POST-only view calls it; Clone buttons are added to the quiz edit page and detail page as plain `<form>` elements.

**Tech Stack:** Django (TestCase, View, atomic transaction); Jinja2 templates; no new dependencies.

## Global Constraints

- Question objects are **shared** (shallow clone) — `QuizQuestion` records are never duplicated.
- Clone resets: `is_public=False`, `start_time=None`, `end_time=None`.
- Code generation: try `{code}2` … `{code}9`; raise `ValueError` if all are taken.
- All tests run via: `docker compose exec site python3 manage.py test quiz.tests.test_clone -v 2` (from `dmoj/`).
- Never skip `{% csrf_token %}` in templates.

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Modify | `quiz/models.py` | Add `Quiz.clone()` + `transaction` import |
| Create | `quiz/tests/test_clone.py` | All tests (model + HTTP) |
| Modify | `quiz/views/editor.py` | Add `QuizClone` view |
| Modify | `quiz/urls.py` | Register `/clone` URL |
| Modify | `templates/quiz/quiz_form.html` | Clone button on edit page |
| Modify | `templates/quiz/detail.html` | Clone button on detail page |

---

### Task 1: `Quiz.clone()` model method

**Files:**
- Modify: `quiz/models.py` (top import + new method on `Quiz`)
- Create: `quiz/tests/test_clone.py`

**Interfaces:**
- Produces: `Quiz.clone(author: Profile) -> Quiz` — raises `ValueError` if no unique code found.

---

- [ ] **Step 1: Create the test file with failing tests**

Create `quiz/tests/test_clone.py`:

```python
from django.test import TestCase
from django.utils import timezone

from quiz.models import Quiz, QuizQuestionLink
from quiz.tests.util import create_organization, create_question, create_quiz, create_user


class QuizCloneModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cloner = create_user(username='cloner', user_permissions=('edit_own_quiz',))
        cls.other_editor = create_user(username='othercloner', user_permissions=('edit_own_quiz',))
        cls.org = create_organization(name='cloneorg', admins=())
        cls.q1 = create_question(title='clone q1', code='cloneq1')
        cls.q2 = create_question(title='clone q2', code='cloneq2')
        cls.quiz = create_quiz(
            code='clonesrc',
            name='Source Quiz',
            description='A description',
            time_limit=45,
            max_attempts=2,
            shuffle_questions=True,
            result_feedback='score_only',
            integrity_monitoring=False,
            is_organization_private=True,
            is_public=True,
            start_time=timezone.now(),
            end_time=timezone.now(),
            authors=(cls.cloner.profile,),
            curators=(cls.other_editor.profile,),
            testers=(),
            organizations=(cls.org,),
            questions=((cls.q1, 2.5), (cls.q2, 1.0)),
        )

    def test_clone_copies_scalar_fields(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertEqual(clone.description, 'A description')
        self.assertEqual(clone.time_limit, 45)
        self.assertEqual(clone.max_attempts, 2)
        self.assertTrue(clone.shuffle_questions)
        self.assertEqual(clone.result_feedback, 'score_only')
        self.assertFalse(clone.integrity_monitoring)
        self.assertTrue(clone.is_organization_private)

    def test_clone_resets_public_and_times(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertFalse(clone.is_public)
        self.assertIsNone(clone.start_time)
        self.assertIsNone(clone.end_time)

    def test_clone_name_prefixed(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertEqual(clone.name, 'Copy of Source Quiz')

    def test_clone_copies_question_links(self):
        clone = self.quiz.clone(self.cloner.profile)
        links = list(clone.question_links.order_by('order'))
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].points, 2.5)
        self.assertEqual(links[1].points, 1.0)
        self.assertEqual(links[0].order, 0)
        self.assertEqual(links[1].order, 1)

    def test_clone_question_links_are_shallow(self):
        clone = self.quiz.clone(self.cloner.profile)
        clone_qids = set(clone.question_links.values_list('question_id', flat=True))
        src_qids = set(self.quiz.question_links.values_list('question_id', flat=True))
        self.assertEqual(clone_qids, src_qids)

    def test_clone_author_is_cloner(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertEqual(list(clone.authors.all()), [self.cloner.profile])

    def test_clone_copies_m2m(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertIn(self.org, clone.organizations.all())
        self.assertIn(self.other_editor.profile, clone.curators.all())

    def test_clone_code_first_suffix(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertEqual(clone.code, 'clonesrc2')

    def test_clone_code_skips_taken_suffixes(self):
        base = create_quiz(code='clonesrck', authors=(self.cloner.profile,))
        create_quiz(code='clonesrck2')
        create_quiz(code='clonesrck3')
        clone = base.clone(self.cloner.profile)
        self.assertEqual(clone.code, 'clonesrck4')

    def test_clone_code_exhausted_raises(self):
        base = create_quiz(code='clonesrce', authors=(self.cloner.profile,))
        for i in range(2, 10):
            create_quiz(code=f'clonesrce{i}')
        with self.assertRaises(ValueError):
            base.clone(self.cloner.profile)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd dmoj
docker compose exec site python3 manage.py test quiz.tests.test_clone -v 2
```

Expected: `AttributeError: 'Quiz' object has no attribute 'clone'`

- [ ] **Step 3: Add `transaction` to the `quiz/models.py` import and implement `Quiz.clone()`**

In `quiz/models.py`, change line 1:
```python
# before
from django.db import models
# after
from django.db import models, transaction
```

Then add this method to the `Quiz` class, after the `regrade_attempts` method:

```python
def clone(self, author):
    suffixes = [str(i) for i in range(2, 10)]
    new_code = None
    for suffix in suffixes:
        candidate = f'{self.code}{suffix}'
        if not Quiz.objects.filter(code=candidate).exists():
            new_code = candidate
            break
    if new_code is None:
        raise ValueError(
            f'Cannot generate a unique code for clone of {self.code!r}')
    with transaction.atomic():
        clone_quiz = Quiz.objects.create(
            code=new_code,
            name=f'Copy of {self.name}',
            description=self.description,
            time_limit=self.time_limit,
            max_attempts=self.max_attempts,
            shuffle_questions=self.shuffle_questions,
            result_feedback=self.result_feedback,
            integrity_monitoring=self.integrity_monitoring,
            is_organization_private=self.is_organization_private,
            is_public=False,
            start_time=None,
            end_time=None,
        )
        clone_quiz.authors.set([author])
        clone_quiz.organizations.set(self.organizations.all())
        clone_quiz.curators.set(self.curators.all())
        clone_quiz.testers.set(self.testers.all())
        QuizQuestionLink.objects.bulk_create([
            QuizQuestionLink(
                quiz=clone_quiz,
                question_id=link.question_id,
                points=link.points,
                order=link.order,
            )
            for link in self.question_links.all()
        ])
    return clone_quiz
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd dmoj
docker compose exec site python3 manage.py test quiz.tests.test_clone -v 2
```

Expected: all `QuizCloneModelTest` tests PASS (HTTP tests will error — they reference `quiz_clone` URL not yet wired).

- [ ] **Step 5: Commit**

```bash
cd dmoj/repo
git add quiz/models.py quiz/tests/test_clone.py
git commit -m "feat(quiz): add Quiz.clone() model method with tests"
```

---

### Task 2: `QuizClone` view + URL + HTTP tests

**Files:**
- Modify: `quiz/views/editor.py` — add `QuizClone` class
- Modify: `quiz/urls.py` — add `quiz_clone` URL
- Modify: `quiz/tests/test_clone.py` — add `QuizCloneViewTest` class

**Interfaces:**
- Consumes: `Quiz.clone(author: Profile) -> Quiz` (from Task 1)
- Produces: URL name `quiz_clone`, accepts `POST /<quiz>/clone`

---

- [ ] **Step 1: Add HTTP tests to `quiz/tests/test_clone.py`**

Append this class to the bottom of the file:

```python
class QuizCloneViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = create_user(
            username='cloneviewauthor', user_permissions=('edit_own_quiz',))
        cls.stranger = create_user(
            username='clonestranger', user_permissions=('edit_own_quiz',))
        cls.q = create_question(title='view clone q', code='viewcloneq')
        cls.quiz = create_quiz(
            code='viewclonesrc',
            authors=(cls.author.profile,),
            questions=((cls.q, 1.0),),
        )

    def test_clone_post_redirects_to_edit(self):
        from django.urls import reverse
        self.client.force_login(self.author)
        resp = self.client.post(
            reverse('quiz_clone', kwargs={'quiz': 'viewclonesrc'}))
        self.assertRedirects(
            resp, reverse('quiz_edit', kwargs={'quiz': 'viewclonesrc2'}))

    def test_clone_creates_quiz_and_links(self):
        from django.urls import reverse
        self.client.force_login(self.author)
        self.client.post(reverse('quiz_clone', kwargs={'quiz': 'viewclonesrc'}))
        clone = Quiz.objects.get(code='viewclonesrc2')
        self.assertEqual(clone.question_links.count(), 1)

    def test_clone_non_editor_returns_404(self):
        from django.urls import reverse
        self.client.force_login(self.stranger)
        resp = self.client.post(
            reverse('quiz_clone', kwargs={'quiz': 'viewclonesrc'}))
        self.assertEqual(resp.status_code, 404)

    def test_clone_get_returns_405(self):
        from django.urls import reverse
        self.client.force_login(self.author)
        resp = self.client.get(
            reverse('quiz_clone', kwargs={'quiz': 'viewclonesrc'}))
        self.assertEqual(resp.status_code, 405)
```

- [ ] **Step 2: Run tests to confirm the new tests fail**

```bash
cd dmoj
docker compose exec site python3 manage.py test quiz.tests.test_clone.QuizCloneViewTest -v 2
```

Expected: `NoReverseMatch` for `quiz_clone`

- [ ] **Step 3: Add `QuizClone` view to `quiz/views/editor.py`**

At the top of `editor.py`, `View` is already imported (line 9). Add after the last class (`QuizViolationLog`):

```python
class QuizClone(QuizEditorObjectMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            clone = self.quiz.clone(request.profile)
        except ValueError:
            messages.error(
                request,
                _('Could not generate a unique code for the clone. '
                  'Rename the original quiz first.'))
            return redirect('quiz_edit', quiz=self.quiz.code)
        messages.success(
            request,
            _('Quiz cloned. Update the name and settings before publishing.'))
        return redirect('quiz_edit', quiz=clone.code)
```

- [ ] **Step 4: Register the URL in `quiz/urls.py`**

Inside the `path('/<str:quiz>', include([...]))` block, add after the `quiz_attempts` line:

```python
path('/clone', editor.QuizClone.as_view(), name='quiz_clone'),
```

The full `/<str:quiz>` group should now read:

```python
path('/<str:quiz>', include([
    path('', student.QuizDetail.as_view(), name='quiz_detail'),
    path('/start', student.QuizStart.as_view(), name='quiz_start'),
    path('/ranking', student.QuizRanking.as_view(), name='quiz_ranking'),
    path('/edit', editor.QuizEdit.as_view(), name='quiz_edit'),
    path('/clone', editor.QuizClone.as_view(), name='quiz_clone'),
    path('/attempts', editor.QuizAttempts.as_view(), name='quiz_attempts'),
    path('/attempt/<int:attempt>', include([
        path('', student.QuizTake.as_view(), name='quiz_take'),
        path('/save', student.QuizSaveAnswer.as_view(), name='quiz_save'),
        path('/violation', student.QuizRecordViolation.as_view(), name='quiz_violation'),
        path('/violations', editor.QuizViolationLog.as_view(), name='quiz_violation_log'),
        path('/submit', student.QuizSubmit.as_view(), name='quiz_submit'),
        path('/result', student.QuizResult.as_view(), name='quiz_result'),
    ])),
])),
```

- [ ] **Step 5: Run all clone tests**

```bash
cd dmoj
docker compose exec site python3 manage.py test quiz.tests.test_clone -v 2
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
cd dmoj/repo
git add quiz/views/editor.py quiz/urls.py quiz/tests/test_clone.py
git commit -m "feat(quiz): add QuizClone view and URL"
```

---

### Task 3: Clone buttons in templates

**Files:**
- Modify: `templates/quiz/quiz_form.html` — Clone button after the save form, edit page only
- Modify: `templates/quiz/detail.html` — Clone button in the editor links area

No new tests needed — the HTTP tests in Task 2 already cover the view; template rendering is covered by existing `QuizEditDynamicFormsetTest`.

---

- [ ] **Step 1: Add Clone button to `templates/quiz/quiz_form.html`**

After the closing `</form>` tag (line 88), and before the closing `</div>` (line 89), insert:

```html
{% if editing %}
<div style="margin-top:0.5em;text-align:right;">
    <form method="post" action="{{ url('quiz_clone', quiz.code) }}" style="display:inline;">
        {% csrf_token %}
        <button type="submit" class="button">{{ _('Clone quiz') }}</button>
    </form>
</div>
{% endif %}
```

The bottom of `{% block body %}` should now look like:

```html
</form>
{% if editing %}
<div style="margin-top:0.5em;text-align:right;">
    <form method="post" action="{{ url('quiz_clone', quiz.code) }}" style="display:inline;">
        {% csrf_token %}
        <button type="submit" class="button">{{ _('Clone quiz') }}</button>
    </form>
</div>
{% endif %}
</div>

<style>
```

- [ ] **Step 2: Add Clone button to `templates/quiz/detail.html`**

Inside the `{% if can_edit %}` block in the `.quiz-links` div (lines 253–261), append the Clone form after the "All attempts" link:

```html
{% if can_edit %}
<a href="{{ url('quiz_edit', quiz.code) }}" class="quiz-edit-link">
    <i class="fa fa-edit"></i> {{ _('Edit quiz') }}
</a>
<a href="{{ url('quiz_attempts', quiz.code) }}" class="quiz-edit-link">
    <i class="fa fa-list"></i> {{ _('All attempts') }}
</a>
<form method="post" action="{{ url('quiz_clone', quiz.code) }}" style="display:inline;margin:0;">
    {% csrf_token %}
    <button type="submit"
            style="background:none;border:none;cursor:pointer;padding:0;font-size:inherit;color:#5b80b9;"
            class="quiz-edit-link">
        <i class="fa fa-copy"></i> {{ _('Clone quiz') }}
    </button>
</form>
{% endif %}
```

- [ ] **Step 3: Run full quiz test suite to check for regressions**

```bash
cd dmoj
docker compose exec site python3 manage.py test quiz -v 2
```

Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
cd dmoj/repo
git add templates/quiz/quiz_form.html templates/quiz/detail.html
git commit -m "feat(quiz): add Clone button to quiz edit and detail pages"
```
