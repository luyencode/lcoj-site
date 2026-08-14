# Quiz Markdown Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add markdown editing experience to quiz question `content` & `explanation` fields (frontend + admin) and quiz `description` (admin), so authors can write and preview markdown while editing.

**Architecture:** (1) A new `QuizMarkdownPreviewView` POST endpoint in `quiz/views/preview.py` that renders markdown server-side using the existing `'default'` style — identical to what `take.html` and `result.html` already display. (2) A lightweight Write/Preview tab widget injected via JS into `question_form.html` and `quiz_form.html`, using `fetch()` against that endpoint. (3) `AdminMartorWidget` wired in `quiz/admin.py` for the same three fields — the same pattern used by every other admin form in this codebase.

**Tech Stack:** Django class-based views, existing `MarkdownPreviewView` base class (`judge/views/preview.py`), `AdminMartorWidget` / `MartorWidget` from `judge.widgets`, vanilla JS `fetch()` + CSRF token from form, Jinja2 templates.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `quiz/views/preview.py` | `QuizMarkdownPreviewView` POST handler |
| Create | `templates/quiz/preview.html` | Jinja2 template: render `preview_data\|markdown('default')` |
| Modify | `quiz/urls.py` | Register `/preview` route, import preview view |
| Modify | `quiz/admin.py` | `AdminMartorWidget` for `content`, `explanation`, `description` |
| Modify | `templates/quiz/question_form.html` | Write/Preview tabs on `content` + `explanation` |
| Modify | `templates/quiz/quiz_form.html` | Write/Preview tab on `description` via JS |

---

## Task 1: Quiz preview endpoint

**Files:**
- Create: `quiz/views/preview.py`
- Create: `templates/quiz/preview.html`
- Modify: `quiz/urls.py`

- [ ] **Step 1: Create the preview view**

Create `quiz/views/preview.py`:

```python
from judge.views.preview import MarkdownPreviewView


class QuizMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'quiz/preview.html'
```

- [ ] **Step 2: Create the preview template**

Create `templates/quiz/preview.html`:

```
{{ preview_data|markdown('default') }}
```

- [ ] **Step 3: Register the URL**

In `quiz/urls.py`, add the import and route:

```python
from django.urls import include, path

from quiz.views import editor, importer, student
from quiz.views.preview import QuizMarkdownPreviewView   # ← add

urlpatterns = [
    path('/', student.QuizList.as_view(), name='quiz_list'),
    path('/preview', QuizMarkdownPreviewView.as_view(), name='quiz_preview'),   # ← add
    path('/questions', include([
        path('/', editor.QuestionBank.as_view(), name='quiz_question_bank'),
        path('/new', editor.QuestionCreate.as_view(), name='quiz_question_create'),
        path('/<int:question>/edit', editor.QuestionEdit.as_view(),
             name='quiz_question_edit'),
    ])),
    path('/import', include([
        path('/', importer.QuizImport.as_view(), name='quiz_import'),
        path('/confirm', importer.QuizImportConfirm.as_view(),
             name='quiz_import_confirm'),
        path('/template', importer.QuizImportTemplate.as_view(),
             name='quiz_import_template'),
    ])),
    path('/export', importer.QuizExport.as_view(), name='quiz_export'),
    path('/new', editor.QuizEdit.as_view(), name='quiz_create'),
    path('/<str:quiz>', include([
        path('', student.QuizDetail.as_view(), name='quiz_detail'),
        path('/start', student.QuizStart.as_view(), name='quiz_start'),
        path('/ranking', student.QuizRanking.as_view(), name='quiz_ranking'),
        path('/edit', editor.QuizEdit.as_view(), name='quiz_edit'),
        path('/attempts', editor.QuizAttempts.as_view(), name='quiz_attempts'),
        path('/attempt/<int:attempt>', include([
            path('', student.QuizTake.as_view(), name='quiz_take'),
            path('/save', student.QuizSaveAnswer.as_view(), name='quiz_save'),
            path('/submit', student.QuizSubmit.as_view(), name='quiz_submit'),
            path('/result', student.QuizResult.as_view(), name='quiz_result'),
        ])),
    ])),
]
```

- [ ] **Step 4: Smoke-test the endpoint manually**

With the dev server running, POST to `/quizzes/preview` from the browser console:

```javascript
fetch('/quizzes/preview', {
  method: 'POST',
  headers: {'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value},
  body: 'content=**hello**'
}).then(r => r.text()).then(console.log)
```

Expected: `<p><strong>hello</strong></p>` (or similar rendered HTML).

- [ ] **Step 5: Commit**

```bash
git add quiz/views/preview.py templates/quiz/preview.html quiz/urls.py
git commit -m "feat(quiz): add markdown preview endpoint /quizzes/preview"
```

---

## Task 2: Admin — wire AdminMartorWidget

**Files:**
- Modify: `quiz/admin.py` (lines 1–57)

The `AdminMartorWidget` from `judge.widgets` is the project-standard markdown editor for admin forms. It adds an Ace-editor toolbar + live-preview tab. We wire it for `content` and `explanation` on `QuizQuestionAdminForm`, and `description` on `QuizAdminForm`. We point them all at the new `quiz_preview` URL.

- [ ] **Step 1: Update `quiz/admin.py`**

Replace the import line and both form `Meta.widgets` dicts:

```python
from django.contrib import admin, messages
from django.db import transaction
from django.forms import ModelForm
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse, reverse_lazy          # ← add reverse_lazy
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from judge.widgets import AdminHeavySelect2MultipleWidget, AdminMartorWidget   # ← add AdminMartorWidget
from quiz.forms import QuizImportForm
from quiz.importers import json_fmt, xlsx_fmt
from quiz.importers.base import ParsedQuestion
from quiz.models import (Quiz, QuizAnswer, QuizAttempt, QuizCategory,
                         QuizQuestion, QuizQuestionLink)
```

Update `QuizQuestionAdminForm.Meta.widgets`:

```python
class QuizQuestionAdminForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['authors'].widget.can_add_related = False
        self.fields['curators'].widget.can_add_related = False

    class Meta:
        model = QuizQuestion
        fields = '__all__'
        widgets = {
            'authors': AdminHeavySelect2MultipleWidget(
                data_view='profile_select2'),
            'curators': AdminHeavySelect2MultipleWidget(
                data_view='profile_select2'),
            'content': AdminMartorWidget(
                attrs={'data-markdownfy-url': reverse_lazy('quiz_preview')}),
            'explanation': AdminMartorWidget(
                attrs={'data-markdownfy-url': reverse_lazy('quiz_preview')}),
        }
```

Update `QuizAdminForm.Meta.widgets`:

```python
class QuizAdminForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['authors'].widget.can_add_related = False
        self.fields['curators'].widget.can_add_related = False
        self.fields['testers'].widget.can_add_related = False

    class Meta:
        model = Quiz
        fields = '__all__'
        widgets = {
            'authors': AdminHeavySelect2MultipleWidget(
                data_view='profile_select2'),
            'curators': AdminHeavySelect2MultipleWidget(
                data_view='profile_select2'),
            'testers': AdminHeavySelect2MultipleWidget(
                data_view='profile_select2'),
            'organizations': AdminHeavySelect2MultipleWidget(
                data_view='organization_select2'),
            'description': AdminMartorWidget(
                attrs={'data-markdownfy-url': reverse_lazy('quiz_preview')}),
        }
```

- [ ] **Step 2: Verify admin pages load**

Open `/admin/quiz/quizquestion/add/` and `/admin/quiz/quiz/add/` in the browser.
- Expected: `content` and `explanation` fields show the Martor editor (Ace editor + Write/Preview tabs in the toolbar).
- `description` on the Quiz admin form shows the same editor.
- No JS console errors.

- [ ] **Step 3: Commit**

```bash
git add quiz/admin.py
git commit -m "feat(quiz): AdminMartorWidget for content, explanation, description in admin"
```

---

## Task 3: Write/Preview tabs in `question_form.html`

**Files:**
- Modify: `templates/quiz/question_form.html`

The existing form has plain `<textarea>` widgets for `content` (line ~211) and `explanation` (line ~218). We wrap each with a `.md-editor` container that shows a **Write** tab (the textarea) and a **Preview** tab (a `<div>` populated via `fetch()`). All JS is added to the existing `{% block content_js_media %}` script at the bottom of the file.

- [ ] **Step 1: Add CSS for the Write/Preview tabs**

Inside the existing `<style>` block (before `</style>`), append:

```css
/* ── Markdown Write/Preview tabs ── */
.md-editor { border: 1px solid #ccc; border-radius: 5px; overflow: hidden; }
.md-editor:focus-within { border-color: #2e7d32; box-shadow: 0 0 0 2px rgba(46,125,50,.1); }
.md-tabs {
    display: flex; background: #f5f5f5;
    border-bottom: 1px solid #ccc;
}
.md-tab {
    background: none; border: none; padding: 6px 16px;
    font-size: 12px; font-weight: 600; color: #666; cursor: pointer;
    border-right: 1px solid #e0e0e0;
}
.md-tab.active { background: #fff; color: #2e7d32; border-bottom: 2px solid #2e7d32; margin-bottom: -1px; }
.md-tab:hover:not(.active) { background: #eee; }
.md-pane-write textarea {
    border: none !important; border-radius: 0 !important;
    box-shadow: none !important; margin: 0; display: block;
}
.md-pane-preview {
    min-height: 80px; padding: 10px 12px;
    font-size: 14px; line-height: 1.6; color: #333;
    background: #fff;
}
.md-pane-preview p:first-child { margin-top: 0; }
.md-preview-loading { color: #aaa; font-style: italic; font-size: 13px; }
.md-preview-empty  { color: #bbb; font-style: italic; font-size: 13px; }
```

- [ ] **Step 2: Wrap the `content` field**

Replace the existing `content` field block (~lines 209–214):

```html
<div class="field-row{% if form.content.errors %} has-error{% endif %}">
    <label>{{ _('Question Text') }} <span class="req">*</span></label>
    <div class="md-editor">
        <div class="md-tabs">
            <button type="button" class="md-tab active" data-pane="write">{{ _('Write') }}</button>
            <button type="button" class="md-tab" data-pane="preview">{{ _('Preview') }}</button>
        </div>
        <div class="md-pane-write">{{ form.content }}</div>
        <div class="md-pane-preview" style="display:none;"></div>
    </div>
    {% for e in form.content.errors %}<div class="field-error">{{ e }}</div>{% endfor %}
    <div class="field-hint">{{ _('Supports Markdown — **bold**, *italic*, `code`, $math$') }}</div>
</div>
```

- [ ] **Step 3: Wrap the `explanation` field**

Replace the existing `explanation` field block (~lines 216–220):

```html
<div class="field-row">
    <label>{{ _('Overall Explanation') }}</label>
    <div class="md-editor">
        <div class="md-tabs">
            <button type="button" class="md-tab active" data-pane="write">{{ _('Write') }}</button>
            <button type="button" class="md-tab" data-pane="preview">{{ _('Preview') }}</button>
        </div>
        <div class="md-pane-write">{{ form.explanation }}</div>
        <div class="md-pane-preview" style="display:none;"></div>
    </div>
    <div class="field-hint">{{ _('Shown to all students after submitting, regardless of their answer. Supports Markdown.') }}</div>
</div>
```

- [ ] **Step 4: Add the Write/Preview JS**

Inside the existing `<script>` block in `{% block content_js_media %}`, add this function call at the very end (after the existing `})();` closing line):

```javascript
/* ── Markdown Write/Preview tabs ── */
(function () {
'use strict';

var PREVIEW_URL = {{ url('quiz_preview')|tojson }};
var CSRF = document.querySelector('[name=csrfmiddlewaretoken]').value;

document.querySelectorAll('.md-editor').forEach(function (editor) {
    var writePane   = editor.querySelector('.md-pane-write');
    var previewPane = editor.querySelector('.md-pane-preview');
    var textarea    = writePane.querySelector('textarea');

    editor.querySelectorAll('.md-tab').forEach(function (tab) {
        tab.addEventListener('click', function () {
            editor.querySelectorAll('.md-tab').forEach(function (t) {
                t.classList.remove('active');
            });
            tab.classList.add('active');

            if (tab.dataset.pane === 'write') {
                writePane.style.display = '';
                previewPane.style.display = 'none';
            } else {
                writePane.style.display = 'none';
                previewPane.style.display = '';

                var content = textarea.value.trim();
                if (!content) {
                    previewPane.innerHTML = '<span class="md-preview-empty">{{ _("Nothing to preview.") }}</span>';
                    return;
                }

                previewPane.innerHTML = '<span class="md-preview-loading">{{ _("Loading preview…") }}</span>';
                fetch(PREVIEW_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': CSRF,
                    },
                    body: 'content=' + encodeURIComponent(content),
                })
                .then(function (r) { return r.text(); })
                .then(function (html) { previewPane.innerHTML = html; })
                .catch(function () {
                    previewPane.innerHTML = '<span class="md-preview-empty">{{ _("Preview failed.") }}</span>';
                });
            }
        });
    });
});

})();
```

- [ ] **Step 5: Verify in the browser**

Open `/quizzes/questions/new` or an existing question edit page.
- Both `content` and `explanation` fields show Write / Preview tabs.
- Typing markdown in Write and switching to Preview shows rendered HTML.
- Switching back to Write preserves the typed text.
- No JS console errors.

- [ ] **Step 6: Commit**

```bash
git add templates/quiz/question_form.html
git commit -m "feat(quiz): Write/Preview markdown tabs on question content and explanation"
```

---

## Task 4: Write/Preview tab in `quiz_form.html`

**Files:**
- Modify: `templates/quiz/quiz_form.html`

`quiz_form.html` currently uses `form.as_p()` which auto-renders all fields. Since `description` is a multi-line `TextField`, we render it manually outside `as_p()` with a tab wrapper, and exclude it from the auto-render by switching to explicit field-by-field rendering — but that's too invasive. Instead we use a JS-based approach: inject tabs around the `#id_description` textarea after page load, identical to what the admin `change_form.html` already does.

- [ ] **Step 1: Add a `{% block body_media %}` or inline `<script>` at the bottom of `quiz_form.html`**

In `quiz_form.html`, add a `<style>` and `<script>` block at the end of `{% block body %}`, right before `{% endblock %}`. The CSS is the same `.md-editor` / `.md-tab` etc. defined in Task 3 Step 1 (copy it). The JS finds `#id_description` and wraps it:

```html
{% block body %}
<form method="post">
    {% csrf_token %}
    {{ form.as_p() }}
    {# ... rest of existing form ... #}
</form>
{# ... rest of existing block ... #}

<style>
/* ── Markdown Write/Preview tabs ── */
.md-editor { border: 1px solid #ccc; border-radius: 4px; overflow: hidden; margin-top: 4px; }
.md-tabs { display: flex; background: #f5f5f5; border-bottom: 1px solid #ccc; }
.md-tab {
    background: none; border: none; padding: 5px 14px;
    font-size: 12px; font-weight: 600; color: #666; cursor: pointer;
    border-right: 1px solid #e0e0e0;
}
.md-tab.active { background: #fff; color: #417690; border-bottom: 2px solid #417690; margin-bottom: -1px; }
.md-tab:hover:not(.active) { background: #eee; }
.md-pane-write textarea { border: none !important; border-radius: 0 !important; display: block; margin: 0; width: 100%; box-sizing: border-box; }
.md-pane-preview { min-height: 60px; padding: 10px 12px; font-size: 14px; line-height: 1.6; background: #fff; }
.md-preview-loading, .md-preview-empty { color: #aaa; font-style: italic; font-size: 13px; }
</style>
<script>
(function () {
'use strict';

var PREVIEW_URL = {{ url('quiz_preview')|tojson }};
var CSRF = document.querySelector('[name=csrfmiddlewaretoken]').value;

var textarea = document.getElementById('id_description');
if (!textarea) return;

/* Wrap the textarea in the tab structure */
var wrapper = document.createElement('div');
wrapper.className = 'md-editor';
wrapper.innerHTML =
    '<div class="md-tabs">' +
    '<button type="button" class="md-tab active" data-pane="write">{{ _("Write") }}</button>' +
    '<button type="button" class="md-tab" data-pane="preview">{{ _("Preview") }}</button>' +
    '</div>' +
    '<div class="md-pane-write"></div>' +
    '<div class="md-pane-preview" style="display:none;"></div>';

textarea.parentNode.insertBefore(wrapper, textarea);
wrapper.querySelector('.md-pane-write').appendChild(textarea);

var previewPane = wrapper.querySelector('.md-pane-preview');

wrapper.querySelectorAll('.md-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
        wrapper.querySelectorAll('.md-tab').forEach(function (t) { t.classList.remove('active'); });
        tab.classList.add('active');

        if (tab.dataset.pane === 'write') {
            textarea.parentNode.style.display = '';
            previewPane.style.display = 'none';
        } else {
            textarea.parentNode.style.display = 'none';
            previewPane.style.display = '';
            var content = textarea.value.trim();
            if (!content) {
                previewPane.innerHTML = '<span class="md-preview-empty">{{ _("Nothing to preview.") }}</span>';
                return;
            }
            previewPane.innerHTML = '<span class="md-preview-loading">{{ _("Loading…") }}</span>';
            fetch(PREVIEW_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': CSRF,
                },
                body: 'content=' + encodeURIComponent(content),
            })
            .then(function (r) { return r.text(); })
            .then(function (html) { previewPane.innerHTML = html; })
            .catch(function () {
                previewPane.innerHTML = '<span class="md-preview-empty">{{ _("Preview failed.") }}</span>';
            });
        }
    });
});

})();
</script>
{% endblock %}
```

- [ ] **Step 2: Verify in the browser**

Open `/quizzes/new` or an existing quiz edit page.
- The `description` textarea is wrapped with Write / Preview tabs.
- Switching to Preview renders the markdown.
- Switching back to Write preserves the text.
- Form submits normally (textarea is still in the DOM inside the Write pane).

- [ ] **Step 3: Commit**

```bash
git add templates/quiz/quiz_form.html
git commit -m "feat(quiz): Write/Preview markdown tab on quiz description field"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Admin markdown editor for `QuizQuestion.content` — Task 2
- ✅ Admin markdown editor for `QuizQuestion.explanation` — Task 2
- ✅ Admin markdown editor for `Quiz.description` — Task 2
- ✅ Frontend Write/Preview for `QuizQuestion.content` — Task 3
- ✅ Frontend Write/Preview for `QuizQuestion.explanation` — Task 3
- ✅ Frontend Write/Preview for `Quiz.description` — Task 4
- ✅ Preview endpoint uses `'default'` style, matching `take.html` and `result.html` — Task 1

**Placeholder scan:** None found.

**Type consistency:** `QuizMarkdownPreviewView` defined in Task 1, imported nowhere else. `PREVIEW_URL` + `CSRF` variables defined locally in each JS block, no cross-task dependency.
