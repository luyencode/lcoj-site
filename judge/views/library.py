from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from judge.models import ExamCategory, ExamStatement
from judge.models.library import EXAM_PROVINCES
from judge.utils.diggpaginator import DiggPaginator
from judge.utils.opengraph import generate_opengraph
from judge.utils.views import TitleMixin

# Accent colors cycled across exam categories (by display order) for the
# tab/badge chips on the library pages.
CATEGORY_PALETTE = ['#1f8b3f', '#2e86c9', '#7a4fb5', '#c9762e', '#0e6a54', '#b5384f', '#5b6770']


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
            try:
                year = int(year)
            except ValueError:
                year = None
            if year is not None:
                queryset = queryset.filter(year=year)

        return queryset.order_by('-publish_on')

    def get_context_data(self, **kwargs):
        context = super(LibraryList, self).get_context_data(**kwargs)
        visible = ExamStatement.objects.filter(is_visible=True, publish_on__lte=timezone.now())

        categories = list(ExamCategory.objects.order_by('order', 'name'))
        category_counts = dict(visible.values_list('category__slug')
                               .annotate(c=Count('id')).values_list('category__slug', 'c'))

        context['title'] = _('Library')
        context['first_page_href'] = None
        context['categories'] = categories
        context['category_counts'] = category_counts
        context['category_colors'] = {cat.slug: CATEGORY_PALETTE[i % len(CATEGORY_PALETTE)]
                                      for i, cat in enumerate(categories)}
        context['provinces'] = EXAM_PROVINCES
        context['years'] = (visible.filter(year__isnull=False)
                            .order_by('-year')
                            .values_list('year', flat=True)
                            .distinct())
        context['total_exams'] = visible.count()
        context['total_provinces'] = visible.exclude(province='').values('province').distinct().count()
        context['current_q'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_province'] = self.request.GET.get('province', '')
        context['current_year'] = self.request.GET.get('year', '')
        context['page_prefix'] = reverse('library_list')
        context['page_suffix'] = ('?' + self.request.GET.urlencode()) if self.request.GET else ''

        tab_params = self.request.GET.copy()
        tab_params.pop('category', None)
        tab_params.pop('page', None)
        context['tab_query'] = tab_params.urlencode()
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
        categories = list(ExamCategory.objects.order_by('order', 'name'))
        index = categories.index(self.object.category) if self.object.category in categories else 0
        context['category_color'] = CATEGORY_PALETTE[index % len(CATEGORY_PALETTE)]
        return context
