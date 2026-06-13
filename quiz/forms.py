from django import forms
from django.core.validators import RegexValidator
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from django.urls import reverse_lazy

from judge.widgets import HeavySelect2MultipleWidget, HeavySelect2Widget, MartorWidget
from quiz.importers.base import correct_to_spec, parse_correct_spec
from quiz.models import Quiz, QuizQuestion, QuizQuestionLink


class QuestionForm(forms.ModelForm):
    # Hidden fields populated by JS
    choices_text = forms.CharField(
        label=_('Choices'), required=False,
        widget=forms.HiddenInput(),
        help_text=_('One choice per line (MC/MA only).'))
    choice_explanations_text = forms.CharField(
        label=_('Choice explanations'), required=False,
        widget=forms.HiddenInput(),
        help_text=_('Optional explanation per choice, one per line (used when editing choices).'))
    correct_spec = forms.CharField(
        label=_('Correct answer'), required=False,
        widget=forms.HiddenInput(),
        help_text=_('MC: choice number (e.g. 2). MA: comma list (1,3). '
                    'TF: true/false. SA: answers separated by |, '
                    'prefix re: for regex, cs: for case-sensitive.'))
    # SA: one regex pattern per line (use (?i) prefix for case-insensitive)
    sa_patterns = forms.CharField(
        label=_('Regex patterns'), required=False,
        widget=forms.HiddenInput(),
        help_text=_('One regex pattern per line. Any match = correct.'))

    class Meta:
        model = QuizQuestion
        fields = ('code', 'type', 'title', 'content', 'category', 'level',
                  'explanation', 'answer_display', 'shuffle_choices',
                  'ma_grading_strategy', 'is_public')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            choices = self.instance.choices or []
            if choices and isinstance(choices[0], dict):
                self.fields['choices_text'].initial = '\n'.join(
                    c.get('text', '') for c in choices)
                self.fields['choice_explanations_text'].initial = '\n'.join(
                    c.get('explanation', '') for c in choices)
            else:
                self.fields['choices_text'].initial = '\n'.join(choices)
                self.fields['choice_explanations_text'].initial = ''
            self.fields['correct_spec'].initial = correct_to_spec(
                self.instance.type, self.instance.correct_answers)
            if self.instance.type == 'SA':
                patterns = []
                for a in (self.instance.correct_answers or []):
                    if isinstance(a, dict):
                        patterns.append(a.get('text', ''))
                    else:
                        patterns.append(str(a))
                self.fields['sa_patterns'].initial = '\n'.join(patterns)

    def clean(self):
        cleaned = super().clean()
        qtype = cleaned.get('type')
        choices = [line.strip() for line in
                   (cleaned.get('choices_text') or '').splitlines()
                   if line.strip()]

        if qtype in ('MC', 'MA') and len(choices) < 2:
            self.add_error('choices_text',
                           _('Provide at least 2 choices.'))

        if qtype:
            # For SA: build correct_spec from sa_answers + sa_regex + sa_case_sensitive
            if qtype == 'SA':
                parts = [p.strip() for p in
                         (cleaned.get('sa_patterns') or '').splitlines()
                         if p.strip()]
                spec = ' | '.join(parts)
                cleaned['correct_spec'] = spec
            else:
                spec = cleaned.get('correct_spec', '')

            correct, errors = parse_correct_spec(
                qtype, spec, len(choices))
            for error in errors:
                self.add_error('correct_spec', error)
            cleaned['parsed_choices'] = choices \
                if qtype in ('MC', 'MA') else []
            cleaned['parsed_correct'] = correct

        return cleaned

    def save(self, commit=True):
        cleaned_data = self.cleaned_data
        parsed_choices = cleaned_data['parsed_choices']
        raw_explanations = [
            line.strip() for line in
            (cleaned_data.get('choice_explanations_text') or '').splitlines()
        ]
        # Pad or trim explanations to match number of choices
        num_choices = len(parsed_choices)
        if len(raw_explanations) < num_choices:
            raw_explanations += [''] * (num_choices - len(raw_explanations))
        else:
            raw_explanations = raw_explanations[:num_choices]
        self.instance.choices = [
            {'text': text, 'explanation': expl}
            for text, expl in zip(parsed_choices, raw_explanations)
        ]
        self.instance.correct_answers = cleaned_data['parsed_correct']
        return super().save(commit)


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ('code', 'name', 'description',
                  'time_limit', 'max_attempts', 'shuffle_questions',
                  'result_feedback', 'integrity_monitoring',
                  'is_public', 'is_organization_private', 'organizations',
                  'curators', 'testers')
        widgets = {
            'description': MartorWidget(
                attrs={'data-markdownfy-url': reverse_lazy('quiz_preview')}),
            'organizations': HeavySelect2MultipleWidget(
                data_view='organization_select2',
                attrs={'style': 'width: 100%'}),
            'curators': HeavySelect2MultipleWidget(
                data_view='profile_select2',
                attrs={'style': 'width: 100%'}),
            'testers': HeavySelect2MultipleWidget(
                data_view='profile_select2',
                attrs={'style': 'width: 100%'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['code'].disabled = True


class QuizImportForm(forms.Form):
    file = forms.FileField(label=_('XLSX or JSON file'))
    create_quiz = forms.BooleanField(
        label=_('Also create a quiz from these questions'), required=False)
    quiz_code = forms.CharField(
        label=_('Quiz code'), required=False, max_length=32,
        validators=[RegexValidator('^[a-z0-9]+$',
                                   _('Quiz code must be ^[a-z0-9]+$'))],
    )
    quiz_name = forms.CharField(label=_('Quiz name'), required=False,
                                max_length=100)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('create_quiz'):
            if not cleaned.get('quiz_code') or not cleaned.get('quiz_name'):
                raise forms.ValidationError(
                    _('Quiz code and name are required '
                      'when creating a quiz.'))
            if Quiz.objects.filter(code=cleaned['quiz_code']).exists():
                raise forms.ValidationError(
                    _('A quiz with this code already exists.'))
        return cleaned


class QuizQuestionLinkForm(forms.ModelForm):
    class Meta:
        model = QuizQuestionLink
        fields = ('question', 'points', 'order')
        widgets = {
            'question': HeavySelect2Widget(
                data_view='quiz_question_select2',
                attrs={'style': 'width: 100%'},
            ),
            'order': forms.HiddenInput(attrs={'class': 'order-field'}),
        }


QuizQuestionLinkFormSet = inlineformset_factory(
    Quiz, QuizQuestionLink, form=QuizQuestionLinkForm,
    extra=0, can_delete=True)
