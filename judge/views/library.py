from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, ListView

from judge.models import ExamCategory, ExamStatement
from judge.models.library import EXAM_PROVINCES
from judge.utils.diggpaginator import DiggPaginator
from judge.utils.opengraph import generate_opengraph
from judge.utils.views import TitleMixin


class LibraryList(ListView):
    model = ExamStatement
    template_name = 'library/list.html'
    context_object_name = 'exams'
    paginate_by = 12

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        return DiggPaginator(queryset, per_page, body=6, padding=2,
                             orphans=orphans, allow_empty_first_page=allow_empty_first_page, **kwargs)

    def get_queryset(self):
        queryset = (ExamStatement.objects
                    .filter(is_visible=True, publish_on__lte=timezone.now())
                    .select_related('category', 'contest'))

        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(description__icontains=q))

        category = self.request.GET.get('category', '').strip()
        if category:
            queryset = queryset.filter(category__slug=category)

        province = self.request.GET.get('province', '').strip()
        if province:
            queryset = queryset.filter(province=province)

        year = self.request.GET.get('year', '').strip()
        if year:
            queryset = queryset.filter(year=year)

        return queryset.order_by('-publish_on')

    def get_context_data(self, **kwargs):
        context = super(LibraryList, self).get_context_data(**kwargs)
        context['first_page_href'] = None
        context['categories'] = ExamCategory.objects.order_by('order', 'name')
        context['provinces'] = EXAM_PROVINCES
        context['years'] = (ExamStatement.objects
                            .filter(is_visible=True, year__isnull=False)
                            .order_by('-year')
                            .values_list('year', flat=True)
                            .distinct())
        context['current_q'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_province'] = self.request.GET.get('province', '')
        context['current_year'] = self.request.GET.get('year', '')
        context['page_prefix'] = reverse('library_list')
        context['page_suffix'] = ('?' + self.request.GET.urlencode()) if self.request.GET else ''
        return context


class LibraryDetail(TitleMixin, DetailView):
    model = ExamStatement
    template_name = 'library/detail.html'
    context_object_name = 'exam'

    def get_title(self):
        return self.object.title

    def get_queryset(self):
        return (ExamStatement.objects
                .filter(is_visible=True, publish_on__lte=timezone.now())
                .select_related('category', 'contest'))

    def get_context_data(self, **kwargs):
        context = super(LibraryDetail, self).get_context_data(**kwargs)
        metadata = generate_opengraph('generated-meta-library:%d' % self.object.id,
                                      self.object.description or self.object.title, 'default')
        context['meta_description'] = metadata[0]
        context['og_image'] = metadata[1]
        return context
