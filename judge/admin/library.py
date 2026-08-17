from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.validators import FileExtensionValidator
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _

from judge.models import ExamCategory, ExamStatement
from judge.views.widgets import pdf_statement_uploader


class ExamStatementAdminForm(forms.ModelForm):
    pdf_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=settings.PDF_STATEMENT_SAFE_EXTS)],
        help_text=_('Maximum file size is %s.') % filesizeformat(settings.PDF_STATEMENT_MAX_FILE_SIZE),
        widget=forms.FileInput(attrs={'accept': 'application/pdf'}),
        label=_('PDF file'),
    )

    # publish_on has a model default (timezone.now); the form field must be
    # optional so the default applies when left blank.
    publish_on = forms.DateTimeField(required=False)

    class Meta:
        model = ExamStatement
        fields = '__all__'

    def clean_pdf_file(self):
        content = self.cleaned_data.get('pdf_file')
        if content is not None and content.size > settings.PDF_STATEMENT_MAX_FILE_SIZE:
            raise forms.ValidationError(
                _('File size is too big! Maximum file size is %s') %
                filesizeformat(settings.PDF_STATEMENT_MAX_FILE_SIZE))
        return content


class ExamStatementAdmin(admin.ModelAdmin):
    form = ExamStatementAdminForm
    list_display = ('title', 'category', 'province', 'year', 'contest', 'is_visible', 'publish_on')
    list_filter = ('category', 'province', 'year', 'is_visible')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('pdf_url',)
    date_hierarchy = 'publish_on'

    def save_model(self, request, obj, form, change):
        pdf_file = form.cleaned_data.get('pdf_file')
        if pdf_file is not None:
            obj.pdf_url = pdf_statement_uploader(pdf_file)
        super(ExamStatementAdmin, self).save_model(request, obj, form, change)


class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')
