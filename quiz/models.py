import random
from datetime import timedelta
from functools import cached_property

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from judge.models.profile import Organization, Profile
from quiz import grading


class QuizLevel(models.TextChoices):
    EASY = 'easy', _('Easy')
    MEDIUM = 'medium', _('Medium')
    HARD = 'hard', _('Hard')


class QuestionType(models.TextChoices):
    MULTIPLE_CHOICE = grading.MC, _('Multiple Choice')
    MULTIPLE_ANSWER = grading.MA, _('Multiple Answer')
    TRUE_FALSE = grading.TF, _('True/False')
    SHORT_ANSWER = grading.SA, _('Short Answer')


MA_STRATEGY_CHOICES = [
    (grading.MA_ALL_OR_NOTHING, _('All or nothing')),
    (grading.MA_PARTIAL_CREDIT, _('Partial credit with penalty')),
    (grading.MA_RIGHT_MINUS_WRONG, _('Right minus wrong')),
    (grading.MA_CORRECT_ONLY, _('Correct only, no penalty')),
]


class ResultFeedback(models.TextChoices):
    SCORE_ONLY = 'score_only', _('Score only')
    CORRECTNESS = 'correctness', _('Show correctness (no answer key)')
    FULL = 'full', _('Show correct answers and explanations')


class ViolationType(models.TextChoices):
    TAB_SWITCH = 'tab_switch', _('Tab switch')
    WINDOW_BLUR = 'window_blur', _('Window blur')
    DEVTOOLS = 'devtools', _('DevTools opened')
    PRINT_SCREEN = 'print_screen', _('PrintScreen key')
    COPY_ATTEMPT = 'copy_attempt', _('Copy attempt')


class QuizCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('name'), unique=True)
    slug = models.SlugField(max_length=100, verbose_name=_('slug'), unique=True)
    description = models.TextField(verbose_name=_('description'), blank=True)

    class Meta:
        ordering = ('name',)
        verbose_name = _('quiz category')
        verbose_name_plural = _('quiz categories')

    def __str__(self):
        return self.name


class QuizQuestion(models.Model):
    code = models.CharField(
        max_length=32, unique=True, verbose_name=_('question code'),
        validators=[RegexValidator('^[a-z0-9]+$',
                                   _('Question code must be ^[a-z0-9]+$'))],
    )
    type = models.CharField(max_length=2, verbose_name=_('question type'),
                            choices=QuestionType.choices,
                            default=QuestionType.MULTIPLE_CHOICE)
    title = models.CharField(max_length=200, verbose_name=_('title'),
                             help_text=_('Short name to identify this question in the bank.'))
    content = models.TextField(verbose_name=_('question body'))
    choices = models.JSONField(verbose_name=_('choices'), default=list, blank=True,
                               help_text=_('List of choice texts (MC/MA only).'))
    correct_answers = models.JSONField(
        verbose_name=_('correct answers'), null=True, blank=True,
        help_text=_('MC/TF: choice index. MA: list of indices. '
                    'SA: list of {text, case_sensitive, is_regex}.'))
    explanation = models.TextField(
        verbose_name=_('explanation'), blank=True,
        help_text=_('Shown on the result page when the quiz allows it.'))
    answer_display = models.CharField(
        max_length=500, blank=True, verbose_name=_('answer display'),
        help_text=_('SA only: human-readable answer shown to students on the '
                    'result page. Leave blank to show the raw patterns.'))
    category = models.ForeignKey(
        QuizCategory, verbose_name=_('category'), null=True, blank=True,
        on_delete=models.SET_NULL, related_name='questions')
    level = models.CharField(
        max_length=6, verbose_name=_('level'), choices=QuizLevel.choices,
        default=QuizLevel.EASY)
    shuffle_choices = models.BooleanField(
        verbose_name=_('shuffle choices'), default=False)
    ma_grading_strategy = models.CharField(
        max_length=20, verbose_name=_('MA grading strategy'),
        choices=MA_STRATEGY_CHOICES, default=grading.MA_ALL_OR_NOTHING)
    is_public = models.BooleanField(
        verbose_name=_('publicly visible in bank'), default=False,
        help_text=_('Visible to every quiz editor, not only authors.'))
    authors = models.ManyToManyField(
        Profile, verbose_name=_('creators'), blank=True,
        related_name='authored_quiz_questions')
    curators = models.ManyToManyField(
        Profile, verbose_name=_('curators'), blank=True,
        related_name='curated_quiz_questions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-id',)
        verbose_name = _('quiz question')
        verbose_name_plural = _('quiz questions')
        permissions = (
            ('edit_all_quiz', _('Edit all quizzes and questions')),
            ('edit_own_quiz', _('Edit own quizzes and questions')),
        )

    def __str__(self):
        return f'{self.code}: {self.title}'

    def grade(self, answer):
        return grading.grade(self.type, self.choices, self.correct_answers,
                             self.ma_grading_strategy, answer)

    def is_editable_by(self, user):
        if not user.is_authenticated:
            return False
        if user.has_perm('quiz.edit_all_quiz'):
            return True
        if not user.has_perm('quiz.edit_own_quiz'):
            return False
        return self.authors.filter(id=user.profile.id).exists() or \
            self.curators.filter(id=user.profile.id).exists()

    def is_visible_in_bank(self, user):
        if self.is_editable_by(user):
            return True
        return self.is_public and user.is_authenticated and \
            user.has_perm('quiz.edit_own_quiz')

    @classmethod
    def get_bank_questions(cls, user):
        """Questions this editor may see: their own + public bank questions."""
        if user.has_perm('quiz.edit_all_quiz'):
            return cls.objects.all()
        profile = user.profile
        return cls.objects.filter(
            models.Q(is_public=True) | models.Q(authors=profile) |
            models.Q(curators=profile)).distinct()


class Quiz(models.Model):
    code = models.CharField(
        max_length=32, verbose_name=_('quiz code'), unique=True,
        validators=[RegexValidator('^[a-z0-9]+$',
                                   _('Quiz code must be ^[a-z0-9]+$'))])
    name = models.CharField(max_length=100, verbose_name=_('quiz name'))
    description = models.TextField(verbose_name=_('description'), blank=True)
    time_limit = models.PositiveIntegerField(
        verbose_name=_('time limit (minutes)'), null=True, blank=True,
        help_text=_('Leave blank for unlimited time.'))
    max_attempts = models.PositiveIntegerField(
        verbose_name=_('maximum attempts'), null=True, blank=True,
        help_text=_('Leave blank for unlimited attempts.'))
    shuffle_questions = models.BooleanField(
        verbose_name=_('shuffle questions'), default=False)
    result_feedback = models.CharField(
        max_length=11, choices=ResultFeedback.choices,
        default=ResultFeedback.FULL,
        verbose_name=_('result feedback'),
        help_text=_(
            'Controls what students see on the result page after submitting. '
            '"Score only" — total score, no per-question detail. '
            '"Show correctness" — green/red per question, answer key hidden. '
            '"Show correct answers and explanations" — full feedback.',
        ),
    )
    is_public = models.BooleanField(
        verbose_name=_('publicly visible'), default=False)
    is_organization_private = models.BooleanField(
        verbose_name=_('private to organizations'), default=False)
    organizations = models.ManyToManyField(
        Organization, verbose_name=_('organizations'), blank=True,
        related_name='quizzes')
    authors = models.ManyToManyField(
        Profile, verbose_name=_('creators'), blank=True,
        related_name='authored_quizzes')
    curators = models.ManyToManyField(
        Profile, verbose_name=_('curators'), blank=True,
        related_name='curated_quizzes')
    testers = models.ManyToManyField(
        Profile, verbose_name=_('testers'), blank=True,
        related_name='tested_quizzes',
        help_text=_('These users can take the quiz while it is private.'))
    questions = models.ManyToManyField(
        QuizQuestion, through='QuizQuestionLink', related_name='quizzes')
    integrity_monitoring = models.BooleanField(
        verbose_name=_('integrity monitoring'),
        default=True,
        help_text=_('Track suspicious behavior during this quiz.'),
    )
    start_time = models.DateTimeField(
        verbose_name=_('start time'), null=True, blank=True, db_index=True,
        help_text=_('Leave blank to make the quiz available immediately.'))
    end_time = models.DateTimeField(
        verbose_name=_('end time'), null=True, blank=True, db_index=True,
        help_text=_('Leave blank for no closing time.'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('quiz')
        verbose_name_plural = _('quizzes')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('quiz_detail', args=(self.code,))

    @property
    def total_points(self):
        return self.question_links.aggregate(
            total=models.Sum('points'))['total'] or 0.0

    def is_editable_by(self, user):
        if not user.is_authenticated:
            return False
        if user.has_perm('quiz.edit_all_quiz'):
            return True
        if not user.has_perm('quiz.edit_own_quiz'):
            return False
        return self.authors.filter(id=user.profile.id).exists() or \
            self.curators.filter(id=user.profile.id).exists()

    def is_accessible_by(self, user):
        if self.is_public:
            if not self.is_organization_private:
                return True
            if user.is_authenticated and \
                    self.organizations.filter(
                        id__in=user.profile.organizations.all()).exists():
                return True
        if not user.is_authenticated:
            return False
        if self.is_editable_by(user):
            return True
        return self.testers.filter(id=user.profile.id).exists()

    @classmethod
    def get_visible_quizzes(cls, user):
        if user.is_authenticated and user.has_perm('quiz.edit_all_quiz'):
            return cls.objects.all()
        filters = models.Q(is_public=True, is_organization_private=False)
        if user.is_authenticated:
            profile = user.profile
            filters |= models.Q(is_public=True, is_organization_private=True,
                                organizations__in=profile.organizations.all())
            filters |= models.Q(authors=profile) | models.Q(curators=profile) | \
                models.Q(testers=profile)
        return cls.objects.filter(filters).distinct()

    def regrade_attempts(self):
        count = 0
        for attempt in self.attempts.filter(is_submitted=True):
            attempt.regrade()
            count += 1
        return count

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

    def get_ranking(self):
        best = {}
        for attempt in self.attempts.filter(is_submitted=True).select_related(
                'user__user'):
            key = (-attempt.score, attempt.duration, attempt.submitted_at)
            current = best.get(attempt.user_id)
            if current is None or key < current[0]:
                best[attempt.user_id] = (key, attempt)
        return [attempt for _key, attempt in sorted(
            best.values(), key=lambda pair: pair[0])]

    @cached_property
    def _now(self):
        return timezone.now()

    @cached_property
    def can_start(self):
        return self.start_time is None or self.start_time <= self._now

    @cached_property
    def ended(self):
        return self.end_time is not None and self.end_time < self._now

    @property
    def time_before_start(self):
        if self.start_time and self._now < self.start_time:
            return self.start_time - self._now
        return None

    @property
    def time_before_end(self):
        if self.end_time and self._now < self.end_time:
            return self.end_time - self._now
        return None


class QuizQuestionLink(models.Model):
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name='question_links')
    question = models.ForeignKey(
        QuizQuestion, on_delete=models.CASCADE, related_name='quiz_links')
    points = models.FloatField(
        verbose_name=_('points'), default=1.0,
        validators=[MinValueValidator(0)])
    order = models.IntegerField(verbose_name=_('order'), default=0)

    class Meta:
        unique_together = ('quiz', 'question')
        ordering = ('order', 'id')
        verbose_name = _('quiz question link')
        verbose_name_plural = _('quiz question links')

    def __str__(self):
        return '%s in %s' % (self.question, self.quiz)


class QuizAttempt(models.Model):
    GRACE = timedelta(seconds=30)

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name='quiz_attempts')
    started_at = models.DateTimeField(
        verbose_name=_('started at'), default=timezone.now)
    submitted_at = models.DateTimeField(
        verbose_name=_('submitted at'), null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    score = models.FloatField(verbose_name=_('score'), default=0.0)
    question_order = models.JSONField(default=list)
    choice_orders = models.JSONField(default=dict)

    class Meta:
        indexes = (
            models.Index(fields=('quiz', 'user', 'is_submitted')),
            models.Index(fields=('quiz', 'is_submitted', 'score')),
        )
        verbose_name = _('quiz attempt')
        verbose_name_plural = _('quiz attempts')

    def __str__(self):
        return '%s on %s' % (self.user, self.quiz)

    @classmethod
    def start(cls, quiz, profile):
        links = list(quiz.question_links.select_related('question'))
        order = [link.question_id for link in links]
        if quiz.shuffle_questions:
            random.shuffle(order)
        choice_orders = {}
        for link in links:
            question = link.question
            if question.shuffle_choices and question.choices:
                indices = list(range(len(question.choices)))
                random.shuffle(indices)
                choice_orders[str(question.id)] = indices
        return cls.objects.create(quiz=quiz, user=profile,
                                  question_order=order,
                                  choice_orders=choice_orders)

    @property
    def deadline(self):
        if self.quiz.time_limit is None:
            return None
        return self.started_at + timedelta(minutes=self.quiz.time_limit)

    def has_expired(self, now=None):
        now = now or timezone.now()
        # Personal time limit takes priority: a timed attempt runs to its own
        # deadline even after end_time passes (teachers must set time_limit <=
        # window duration to avoid late submissions in exam settings).
        if self.deadline is not None:
            return now > self.deadline + self.GRACE
        # No personal time limit: quiz end_time is the hard deadline, no grace.
        if self.quiz.end_time is not None:
            return now > self.quiz.end_time
        return False

    def time_remaining_seconds(self, now=None):
        deadline = self.deadline
        if deadline is None:
            return None
        return max(0, int((deadline - (now or timezone.now())).total_seconds()))

    @property
    def duration(self):
        if self.submitted_at is None:
            return None
        return self.submitted_at - self.started_at

    def save_answer(self, question, answer):
        link = self.quiz.question_links.get(question=question)
        ratio, is_correct = question.grade(answer)
        obj, _created = QuizAnswer.objects.update_or_create(
            attempt=self, question=question,
            defaults={'answer': answer,
                      'points': round(ratio * link.points, 2),
                      'is_correct': is_correct})
        return obj

    def _grade_answers(self):
        points_by_question = {link.question_id: link.points
                              for link in self.quiz.question_links.all()}
        total = 0.0
        for answer in self.answers.select_related('question'):
            ratio, is_correct = answer.question.grade(answer.answer)
            answer.points = round(
                ratio * points_by_question.get(answer.question_id, 0.0), 2)
            answer.is_correct = is_correct
            answer.save(update_fields=('points', 'is_correct'))
            total += answer.points
        return round(total, 2)

    def finalize(self, now=None):
        if self.is_submitted:
            return
        now = now or timezone.now()
        self.score = self._grade_answers()
        self.is_submitted = True
        deadline = self.deadline
        self.submitted_at = min(now, deadline) if deadline is not None else now
        self.save(update_fields=('score', 'is_submitted', 'submitted_at'))

    def regrade(self):
        self.score = self._grade_answers()
        self.save(update_fields=('score',))


class QuizAnswer(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(
        QuizQuestion, on_delete=models.CASCADE, related_name='+')
    answer = models.JSONField(null=True, blank=True)
    points = models.FloatField(default=0.0)
    is_correct = models.BooleanField(default=False)
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('attempt', 'question')
        verbose_name = _('quiz answer')
        verbose_name_plural = _('quiz answers')


class QuizViolation(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name='violations')
    type = models.CharField(
        max_length=20, choices=ViolationType.choices)
    occurred_at = models.DateTimeField()
    extra_data = models.JSONField(default=dict)

    class Meta:
        ordering = ['occurred_at']
        indexes = [models.Index(fields=['attempt'])]
        verbose_name = _('quiz violation')
        verbose_name_plural = _('quiz violations')

    def __str__(self):
        return '%s — %s' % (self.attempt, self.get_type_display())
