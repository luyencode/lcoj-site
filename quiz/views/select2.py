from django.db.models import Q
from django.http import Http404

from judge.views.select2 import Select2View
from quiz.models import QuizQuestion


class QuizQuestionSelect2View(Select2View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not (
            request.user.has_perm('quiz.edit_own_quiz') or
            request.user.has_perm('quiz.edit_all_quiz')
        ):
            raise Http404()
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return QuizQuestion.get_bank_questions(self.request.user).filter(
            Q(code__icontains=self.term) |
            Q(title__icontains=self.term) |
            Q(content__icontains=self.term),
        ).only('id', 'code', 'title', 'type')

    def get_name(self, obj):
        return f'[{obj.type}] {obj.code}: {obj.title}'
