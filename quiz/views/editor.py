from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from quiz.forms import QuestionForm, QuizForm, QuizQuestionLinkFormSet
from quiz.models import QuestionType, Quiz, QuizCategory, QuizLevel, QuizQuestion


class EditorPermissionMixin(LoginRequiredMixin):
    """Quiz editors only: edit_own_quiz or edit_all_quiz."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not (
                request.user.has_perm('quiz.edit_own_quiz') or
                request.user.has_perm('quiz.edit_all_quiz')):
            raise Http404()
        return super().dispatch(request, *args, **kwargs)


class QuestionBank(EditorPermissionMixin, ListView):
    template_name = 'quiz/question_bank.html'
    context_object_name = 'questions'
    paginate_by = 50

    def get_queryset(self):
        queryset = QuizQuestion.get_bank_questions(
            self.request.user).select_related('category').order_by('-id')
        if self.request.GET.get('category'):
            queryset = queryset.filter(
                category__slug=self.request.GET['category'])
        if self.request.GET.get('level') in QuizLevel.values:
            queryset = queryset.filter(level=self.request.GET['level'])
        if self.request.GET.get('type') in QuestionType.values:
            queryset = queryset.filter(type=self.request.GET['type'])
        if self.request.GET.get('search'):
            search = self.request.GET['search']
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(title__icontains=search) |
                Q(content__icontains=search))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = QuizCategory.objects.all()
        context['levels'] = QuizLevel.choices
        context['types'] = QuestionType.choices
        return context


class QuestionCreate(EditorPermissionMixin, CreateView):
    model = QuizQuestion
    form_class = QuestionForm
    template_name = 'quiz/question_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.authors.add(self.request.profile)
        return response

    def get_success_url(self):
        return reverse('quiz_question_edit', args=(self.object.id,))


class QuestionEdit(EditorPermissionMixin, UpdateView):
    model = QuizQuestion
    form_class = QuestionForm
    template_name = 'quiz/question_form.html'
    pk_url_kwarg = 'question'

    def get_object(self, queryset=None):
        question = get_object_or_404(QuizQuestion, id=self.kwargs['question'])
        if not question.is_editable_by(self.request.user):
            raise Http404()
        return question

    def get_success_url(self):
        return reverse('quiz_question_edit', args=(self.object.id,))


class QuizEditorObjectMixin(EditorPermissionMixin):
    """Resolves self.quiz by code and requires object-level edit rights."""

    def dispatch(self, request, *args, **kwargs):
        if 'quiz' in kwargs:
            self.quiz = get_object_or_404(Quiz, code=kwargs['quiz'])
            if request.user.is_authenticated and not \
                    self.quiz.is_editable_by(request.user):
                raise Http404()
        else:
            self.quiz = None
        return super().dispatch(request, *args, **kwargs)


class QuizEdit(QuizEditorObjectMixin, TemplateView):
    template_name = 'quiz/quiz_form.html'

    def get_forms(self):
        kwargs = {'instance': self.quiz} if self.quiz else {}
        data = self.request.POST if self.request.method == 'POST' else None
        form = QuizForm(data, **kwargs)
        formset = QuizQuestionLinkFormSet(
            data, instance=self.quiz) if self.quiz else \
            QuizQuestionLinkFormSet(data)
        for link_form in formset.forms:
            link_form.fields['question'].queryset = \
                QuizQuestion.get_bank_questions(self.request.user)
        return form, formset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'], context['formset'] = self.get_forms()
        context['editing'] = self.quiz is not None
        return context

    def post(self, request, *args, **kwargs):
        form, formset = self.get_forms()
        if form.is_valid():
            quiz = form.save()
            if self.quiz is None:
                quiz.authors.add(request.profile)
                formset = QuizQuestionLinkFormSet(request.POST, instance=quiz)
            if formset.is_valid():
                formset.save()
                messages.success(request, _('Quiz saved.'))
                return redirect('quiz_edit', quiz=quiz.code)
            self.quiz = quiz
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset))


class QuizAttempts(QuizEditorObjectMixin, TemplateView):
    template_name = 'quiz/attempts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = self.quiz
        context['attempts'] = self.quiz.attempts.select_related(
            'user__user').order_by('-started_at')
        context['total_points'] = self.quiz.total_points
        return context

    def post(self, request, *args, **kwargs):
        count = self.quiz.regrade_attempts()
        messages.success(request, _('Regraded %d attempts.') % count)
        return redirect('quiz_attempts', quiz=self.quiz.code)
