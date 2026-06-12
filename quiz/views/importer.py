from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.generic import FormView, View

from quiz.forms import QuizImportForm
from quiz.importers import json_fmt, xlsx_fmt
from quiz.importers.base import ParsedQuestion
from quiz.models import Quiz, QuizCategory, QuizQuestion, QuizQuestionLink
from quiz.views.editor import EditorPermissionMixin

SESSION_KEY = 'quiz_import_pending'
XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class QuizImport(EditorPermissionMixin, FormView):
    form_class = QuizImportForm
    template_name = 'quiz/import.html'

    def form_valid(self, form):
        uploaded = form.cleaned_data['file']
        if uploaded.name.lower().endswith('.json'):
            questions = json_fmt.parse(uploaded.read())
        else:
            questions = xlsx_fmt.parse(uploaded)
        # Check for code duplicates within the batch
        seen_codes = {}
        for q in questions:
            if q.code:
                if q.code in seen_codes:
                    q.errors.append(
                        f'Duplicate code {q.code!r} in this file '
                        f'(first seen on row {seen_codes[q.code]})')
                else:
                    seen_codes[q.code] = q.row

        # Check for code conflicts with existing DB records
        batch_codes = {q.code for q in questions if q.code and not q.errors}
        if batch_codes:
            db_conflicts = set(
                QuizQuestion.objects.filter(code__in=batch_codes)
                .values_list('code', flat=True))
            for q in questions:
                if q.code in db_conflicts:
                    q.errors.append(
                        f'Code {q.code!r} already exists in the question bank')

        existing = set(QuizCategory.objects.values_list('slug', flat=True))
        new_categories = sorted({q.category for q in questions
                                 if q.category and q.category not in existing})
        has_errors = any(q.errors for q in questions) or not questions
        if not has_errors:
            self.request.session[SESSION_KEY] = {
                'questions': [q.as_dict() for q in questions],
                'create_quiz': form.cleaned_data['create_quiz'],
                'quiz_code': form.cleaned_data['quiz_code'],
                'quiz_name': form.cleaned_data['quiz_name'],
            }
        return self.render_to_response(self.get_context_data(
            form=form, preview=questions, has_errors=has_errors,
            new_categories=new_categories))


class QuizImportConfirm(EditorPermissionMixin, View):
    def post(self, request, *args, **kwargs):
        payload = request.session.pop(SESSION_KEY, None)
        if payload is None:
            messages.error(request,
                           _('No pending import - upload a file first.'))
            return redirect('quiz_import')
        questions = [ParsedQuestion.from_dict(data)
                     for data in payload['questions']]
        if any(q.errors for q in questions):
            messages.error(request, _('Import file has errors.'))
            return redirect('quiz_import')
        with transaction.atomic():
            categories = {}
            for parsed in questions:
                if parsed.category and parsed.category not in categories:
                    categories[parsed.category], _created = \
                        QuizCategory.objects.get_or_create(
                            slug=parsed.category,
                            defaults={'name': parsed.category.replace(
                                '-', ' ').title()})
            created = []
            for parsed in questions:
                question = QuizQuestion.objects.create(
                    code=parsed.code,
                    type=parsed.type, title=parsed.title,
                    content=parsed.content,
                    choices=parsed.choices,
                    correct_answers=parsed.correct,
                    explanation=parsed.explanation,
                    category=categories.get(parsed.category),
                    level=parsed.level,
                    shuffle_choices=parsed.shuffle,
                    ma_grading_strategy=parsed.ma_strategy)
                question.authors.add(request.profile)
                created.append((question, parsed.points))
            if payload['create_quiz']:
                quiz = Quiz.objects.create(
                    code=payload['quiz_code'],
                    name=payload['quiz_name'])
                quiz.authors.add(request.profile)
                for order, (question, points) in enumerate(created):
                    QuizQuestionLink.objects.create(
                        quiz=quiz, question=question,
                        points=points, order=order)
        messages.success(request,
                         _('Imported %d questions.') % len(created))
        if payload['create_quiz']:
            return redirect('quiz_edit', quiz=payload['quiz_code'])
        return redirect('quiz_question_bank')


class QuizImportTemplate(EditorPermissionMixin, View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(xlsx_fmt.template().read(),
                                content_type=XLSX_MIME)
        response['Content-Disposition'] = \
            'attachment; filename="quiz-template.xlsx"'
        return response


class QuizExport(EditorPermissionMixin, View):
    def get(self, request, *args, **kwargs):
        ids = [int(i) for i in request.GET.getlist('ids')
               if str(i).isdigit()]
        questions = QuizQuestion.get_bank_questions(
            request.user).filter(id__in=ids)
        parsed = [ParsedQuestion(
            row=0, code=q.code, type=q.type, title=q.title, content=q.content,
            choices=q.choices or [], correct=q.correct_answers,
            category=q.category.slug if q.category else '',
            level=q.level, explanation=q.explanation,
            shuffle=q.shuffle_choices,
            ma_strategy=q.ma_grading_strategy) for q in questions]
        response = HttpResponse(xlsx_fmt.write(parsed).read(),
                                content_type=XLSX_MIME)
        response['Content-Disposition'] = \
            'attachment; filename="quiz-questions.xlsx"'
        return response
