from django.contrib import admin, messages
from django.db import transaction
from django.forms import ModelForm
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from judge.widgets import AdminHeavySelect2MultipleWidget, AdminMartorWidget
from quiz.forms import QuizImportForm
from quiz.importers import json_fmt, xlsx_fmt
from quiz.importers.base import ParsedQuestion
from quiz.models import (Quiz, QuizAnswer, QuizAttempt, QuizCategory,
                         QuizQuestion, QuizQuestionLink)

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
SESSION_KEY = 'quiz_admin_import_pending'


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


@admin.register(QuizCategory)
class QuizCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    form = QuizQuestionAdminForm
    change_list_template = 'admin/quiz/quizquestion/change_list.html'
    list_display = ('code', 'title', 'type', 'category', 'level', 'is_public')
    list_filter = ('type', 'level', 'category', 'is_public')
    search_fields = ('code', 'title', 'content')
    fieldsets = (
        (None, {
            'fields': ('code', 'title', 'type', 'content', 'explanation',
                       'category', 'level', 'shuffle_choices',
                       'ma_grading_strategy'),
        }),
        (_l('Choices & Answer'), {
            'fields': ('choices', 'choice_explanations', 'correct_answers'),
        }),
        (_l('Access'), {
            'fields': ('is_public', 'authors', 'curators'),
        }),
    )

    def get_urls(self):
        return [
            path('import/', self.admin_site.admin_view(self.import_view),
                 name='quiz_quizquestion_import'),
            path('import/confirm/', self.admin_site.admin_view(self.import_confirm_view),
                 name='quiz_quizquestion_import_confirm'),
            path('import/template/', self.admin_site.admin_view(self.import_template_view),
                 name='quiz_quizquestion_import_template'),
        ] + super().get_urls()

    def import_view(self, request):
        if request.method == 'POST':
            form = QuizImportForm(request.POST, request.FILES)
            if form.is_valid():
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
                has_errors = any(q.errors for q in questions) or not questions
                if not has_errors:
                    request.session[SESSION_KEY] = {
                        'questions': [q.as_dict() for q in questions],
                        'create_quiz': form.cleaned_data['create_quiz'],
                        'quiz_code': form.cleaned_data['quiz_code'],
                        'quiz_name': form.cleaned_data['quiz_name'],
                    }
                return TemplateResponse(request,
                                        'admin/quiz/quizquestion/import.html',
                                        {**self.admin_site.each_context(request),
                                         'form': form,
                                         'preview': questions,
                                         'has_errors': has_errors,
                                         'title': _('Import Questions')})
        else:
            form = QuizImportForm()
        return TemplateResponse(request, 'admin/quiz/quizquestion/import.html',
                                {**self.admin_site.each_context(request),
                                 'form': form,
                                 'title': _('Import Questions')})

    def import_confirm_view(self, request):
        if request.method != 'POST':
            return HttpResponseRedirect(
                reverse('admin:quiz_quizquestion_import'))
        payload = request.session.pop(SESSION_KEY, None)
        if payload is None:
            messages.error(request,
                           _('No pending import — upload a file first.'))
            return HttpResponseRedirect(
                reverse('admin:quiz_quizquestion_import'))
        questions = [ParsedQuestion.from_dict(d) for d in payload['questions']]
        if any(q.errors for q in questions):
            messages.error(request, _('Import file has errors.'))
            return HttpResponseRedirect(
                reverse('admin:quiz_quizquestion_import'))
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
                if hasattr(request, 'profile'):
                    question.authors.add(request.profile)
                created.append((question, parsed.points))
            if payload['create_quiz']:
                quiz = Quiz.objects.create(
                    code=payload['quiz_code'],
                    name=payload['quiz_name'])
                if hasattr(request, 'profile'):
                    quiz.authors.add(request.profile)
                for order, (question, points) in enumerate(created):
                    QuizQuestionLink.objects.create(
                        quiz=quiz, question=question,
                        points=points, order=order)
        messages.success(request,
                         _('Imported %d questions.') % len(created))
        return HttpResponseRedirect(
            reverse('admin:quiz_quizquestion_changelist'))

    def import_template_view(self, request):
        response = HttpResponse(xlsx_fmt.template().read(),
                                content_type=XLSX_MIME)
        response['Content-Disposition'] = \
            'attachment; filename="quiz-template.xlsx"'
        return response


class QuizQuestionLinkInline(admin.TabularInline):
    model = QuizQuestionLink
    extra = 1
    raw_id_fields = ('question',)
    fields = ('question', 'order', 'points')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    form = QuizAdminForm
    list_display = ('code', 'name', 'category', 'level', 'time_limit',
                    'is_public')
    list_filter = ('level', 'category', 'is_public', 'is_organization_private')
    search_fields = ('code', 'name')
    inlines = (QuizQuestionLinkInline,)
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'description', 'category', 'level'),
        }),
        (_l('Settings'), {
            'fields': ('time_limit', 'max_attempts', 'shuffle_questions',
                       'show_correctness', 'show_answers'),
        }),
        (_l('Access'), {
            'fields': ('is_public', 'is_organization_private',
                       'organizations', 'authors', 'curators', 'testers'),
        }),
    )


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 0
    readonly_fields = ('question', 'answer', 'points', 'is_correct',
                       'saved_at')
    can_delete = False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'user', 'started_at', 'submitted_at',
                    'is_submitted', 'score')
    list_filter = ('is_submitted', 'quiz')
    search_fields = ('user__user__username', 'quiz__code', 'quiz__name')
    readonly_fields = ('quiz', 'user', 'started_at', 'submitted_at',
                       'score', 'question_order', 'choice_orders')
    inlines = (QuizAnswerInline,)
