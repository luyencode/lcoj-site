import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Max, Q, Sum
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.generic import ListView, TemplateView, View

from judge.utils.views import TitleMixin
from quiz.models import Quiz, QuizAttempt, QuizQuestion


class QuizList(TitleMixin, ListView):
    model = Quiz
    template_name = 'quiz/list.html'
    context_object_name = 'quizzes'
    paginate_by = 50
    title = gettext_lazy('Quizzes')

    def get_queryset(self):
        queryset = Quiz.get_visible_quizzes(self.request.user) \
            .order_by('-created_at')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search))
        if self.request.GET.get('hide_attempted') and \
                self.request.user.is_authenticated:
            attempted_ids = QuizAttempt.objects.filter(
                user=self.request.profile, is_submitted=True,
            ).values_list('quiz_id', flat=True).distinct()
            queryset = queryset.exclude(id__in=attempted_ids)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['hide_attempted'] = bool(
            self.request.GET.get('hide_attempted'))
        quiz_ids = [q.pk for q in context['quizzes']]

        best_scores = {}
        if self.request.user.is_authenticated:
            rows = QuizAttempt.objects.filter(
                user=self.request.profile, is_submitted=True,
                quiz_id__in=quiz_ids,
            ).values('quiz_id').annotate(best=Max('score'))
            best_scores = {row['quiz_id']: row['best'] for row in rows}
        context['best_scores'] = best_scores

        max_score_rows = Quiz.objects.filter(pk__in=quiz_ids).annotate(
            max_score=Sum('question_links__points'),
            question_count=Count('question_links'),
        ).values('pk', 'max_score', 'question_count')
        context['max_scores'] = {row['pk']: row['max_score'] or 0 for row in max_score_rows}
        context['question_counts'] = {row['pk']: row['question_count'] for row in max_score_rows}

        stats_rows = QuizAttempt.objects.filter(
            quiz_id__in=quiz_ids, is_submitted=True,
        ).values('quiz_id').annotate(
            attempts=Count('id'),
            users=Count('user', distinct=True),
        )
        context['attempt_counts'] = {row['quiz_id']: row['attempts'] for row in stats_rows}
        context['user_counts'] = {row['quiz_id']: row['users'] for row in stats_rows}

        return context


class QuizMixin:
    """Resolves self.quiz from the URL and 404s if not accessible."""

    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(Quiz, code=kwargs['quiz'])
        if not self.quiz.is_accessible_by(request.user):
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = self.quiz
        return context


class QuizDetail(TitleMixin, QuizMixin, TemplateView):
    template_name = 'quiz/detail.html'

    def get_title(self):
        return self.quiz.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['question_count'] = self.quiz.question_links.count()
        context['total_points'] = self.quiz.total_points
        context['can_edit'] = self.quiz.is_editable_by(self.request.user)
        if self.request.user.is_authenticated:
            attempts = list(self.quiz.attempts.filter(
                user=self.request.profile).order_by('-started_at'))
            for attempt in attempts:
                if not attempt.is_submitted and attempt.has_expired():
                    attempt.finalize()
            context['attempts'] = attempts
            context['in_progress'] = next(
                (a for a in attempts if not a.is_submitted), None)
            if self.quiz.max_attempts is not None:
                used = sum(1 for a in attempts if a.is_submitted)
                context['attempts_left'] = max(
                    0, self.quiz.max_attempts - used)
            else:
                context['attempts_left'] = None
        return context


class QuizStart(LoginRequiredMixin, QuizMixin, View):
    def post(self, request, *args, **kwargs):
        in_progress = self.quiz.attempts.filter(
            user=request.profile, is_submitted=False).first()
        if in_progress is not None:
            if in_progress.has_expired():
                in_progress.finalize()
            else:
                return redirect('quiz_take', quiz=self.quiz.code,
                                attempt=in_progress.id)
        if self.quiz.max_attempts is not None:
            used = self.quiz.attempts.filter(
                user=request.profile, is_submitted=True).count()
            if used >= self.quiz.max_attempts:
                messages.error(
                    request, _('You have no attempts remaining.'))
                return redirect('quiz_detail', quiz=self.quiz.code)
        attempt = QuizAttempt.start(self.quiz, request.profile)
        return redirect('quiz_take', quiz=self.quiz.code, attempt=attempt.id)


class AttemptMixin(QuizMixin):
    """Resolves self.attempt; owner-only unless editor. Lazily finalizes
    expired attempts before any handler runs."""
    allow_editor = False

    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(Quiz, code=kwargs['quiz'])
        if not self.quiz.is_accessible_by(request.user):
            raise Http404()
        self.attempt = get_object_or_404(
            QuizAttempt, id=kwargs['attempt'], quiz=self.quiz)
        is_owner = request.user.is_authenticated and \
            self.attempt.user_id == request.profile.id
        if not is_owner and not (
                self.allow_editor and self.quiz.is_editable_by(request.user)):
            raise Http404()
        if not self.attempt.is_submitted and self.attempt.has_expired():
            self.attempt.finalize()
        return super(QuizMixin, self).dispatch(request, *args, **kwargs)


class QuizTake(TitleMixin, LoginRequiredMixin, AttemptMixin, TemplateView):
    template_name = 'quiz/take.html'

    def get_title(self):
        return self.quiz.name

    def get(self, request, *args, **kwargs):
        if self.attempt.is_submitted:
            return redirect('quiz_result', quiz=self.quiz.code,
                            attempt=self.attempt.id)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questions = {q.id: q for q in QuizQuestion.objects.filter(
            id__in=self.attempt.question_order)}
        answers = {a.question_id: a.answer
                   for a in self.attempt.answers.all()}
        items = []
        for number, question_id in enumerate(
                self.attempt.question_order, start=1):
            question = questions.get(question_id)
            if question is None:
                continue
            choice_indices = self.attempt.choice_orders.get(
                str(question_id)) or list(range(len(question.choices or [])))
            items.append({
                'number': number,
                'question': question,
                'choice_indices': choice_indices,
                'answer': answers.get(question_id),
            })
        context['items'] = items
        context['attempt'] = self.attempt
        context['time_remaining'] = self.attempt.time_remaining_seconds()
        return context


class QuizSubmit(LoginRequiredMixin, AttemptMixin, View):
    def post(self, request, *args, **kwargs):
        if not self.attempt.is_submitted:
            self.attempt.finalize()
        return redirect('quiz_result', quiz=self.quiz.code,
                        attempt=self.attempt.id)


def _normalize_answer(question, answer):
    """Validate the client payload for the question type. Raises ValueError."""
    if answer is None:
        return None
    if question.type in ('MC', 'TF'):
        index = int(answer)
        limit = 2 if question.type == 'TF' else len(question.choices or [])
        if not 0 <= index < limit:
            raise ValueError('choice index out of range')
        return index
    if question.type == 'MA':
        if not isinstance(answer, list):
            raise ValueError('MA answer must be a list')
        indices = sorted({int(i) for i in answer})
        if indices and not (
                0 <= indices[0] and indices[-1] < len(
                    question.choices or [])):
            raise ValueError('choice index out of range')
        return indices or None
    if not isinstance(answer, str):
        raise ValueError('SA answer must be a string')
    return answer[:10000]


class QuizSaveAnswer(LoginRequiredMixin, AttemptMixin, View):
    def post(self, request, *args, **kwargs):
        if self.attempt.is_submitted:
            return JsonResponse({'error': 'attempt_closed'}, status=400)
        try:
            body = json.loads(request.body)
            question_id = int(body['question'])
            raw_answer = body.get('answer')
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return HttpResponseBadRequest()
        if question_id not in self.attempt.question_order:
            return HttpResponseBadRequest()
        try:
            question = QuizQuestion.objects.get(id=question_id)
            answer = _normalize_answer(question, raw_answer)
        except (QuizQuestion.DoesNotExist, TypeError, ValueError):
            return HttpResponseBadRequest()
        self.attempt.save_answer(question, answer)
        return JsonResponse({'saved': True})


class QuizResult(TitleMixin, LoginRequiredMixin, AttemptMixin, TemplateView):
    template_name = 'quiz/result.html'
    allow_editor = True

    def get_title(self):
        return _('%s — Result') % self.quiz.name

    def get(self, request, *args, **kwargs):
        if not self.attempt.is_submitted:
            return redirect('quiz_take', quiz=self.quiz.code,
                            attempt=self.attempt.id)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_edit = self.quiz.is_editable_by(self.request.user)
        feedback = self.quiz.result_feedback
        if can_edit:
            feedback = 'full'
        show_correctness = feedback in ('correctness', 'full')
        show_answers = feedback == 'full'
        questions = {q.id: q for q in QuizQuestion.objects.filter(
            id__in=self.attempt.question_order)}
        answers = {a.question_id: a
                   for a in self.attempt.answers.all()}
        links = {link.question_id: link
                 for link in self.quiz.question_links.all()}
        rows = []
        for number, question_id in enumerate(
                self.attempt.question_order, start=1):
            question = questions.get(question_id)
            if question is None:
                continue
            rows.append({
                'number': number,
                'question': question,
                'answer': answers.get(question_id),
                'max_points': links[question_id].points
                if question_id in links else 0,
            })
        context.update({
            'attempt': self.attempt,
            'rows': rows,
            'total_points': self.quiz.total_points,
            'show_correctness': show_correctness,
            'show_answers': show_answers,
        })
        return context


class QuizRanking(TitleMixin, QuizMixin, TemplateView):
    template_name = 'quiz/ranking.html'

    def get_title(self):
        return _('%s — Ranking') % self.quiz.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ranking'] = self.quiz.get_ranking()
        context['total_points'] = self.quiz.total_points
        context['my_profile_id'] = self.request.profile.id \
            if self.request.user.is_authenticated else None
        return context
