import json

from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext
from django.views.generic import DetailView, ListView

from judge.models import ExamCategory, ExamStatement
from judge.models.library import EXAM_PROVINCES
from judge.utils.diggpaginator import DiggPaginator
from judge.utils.opengraph import generate_opengraph
from judge.utils.views import TitleMixin

# Accent colors cycled across exam categories (by display order) for the
# tab/badge chips on the library pages.
CATEGORY_PALETTE = ['#1f8b3f', '#2e86c9', '#7a4fb5', '#c9762e', '#0e6a54', '#b5384f', '#5b6770']

# Publisher block reused by the schema.org payload of both library pages.
PUBLISHER_NAME = 'Cô Thi Lập Trình'
PUBLISHER_URL = 'https://cothilaptrinh.vn'


def dump_json_ld(payload):
    """Serialise a schema.org payload for inlining in a <script> tag.

    The angle brackets are escaped so a stray ``</script>`` inside any
    user-entered exam title cannot break out of the tag.
    """
    return (json.dumps(payload, ensure_ascii=False)
            .replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))


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
        # Only count the categories that actually hold a published exam, so the
        # headline figure matches the number of tabs shown just below it.
        context['total_categories'] = sum(1 for cat in categories if category_counts.get(cat.slug))
        context['total_provinces'] = visible.exclude(province='').values('province').distinct().count()
        context['total_with_contest'] = visible.filter(contest__isnull=False).count()
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

        # --- Search engine metadata -------------------------------------
        # Every figure below is read from the database on each request, so the
        # title and description of a filtered page describe exactly what that
        # page lists.
        matched = context['page_obj'].paginator.count
        context['title'] = self.get_seo_title(categories)
        context['meta_description'] = self.get_meta_description(matched)
        # Free-text searches produce endless thin permutations of the same
        # listing, so let crawlers follow the links but keep those pages out of
        # the index. The category/province/year facets stay indexable.
        context['seo_noindex'] = bool(self.request.GET.get('q', '').strip())
        context['structured_data'] = dump_json_ld(self.get_structured_data(context, matched))
        return context

    def get_active_filter_labels(self, categories):
        """Human-readable labels for the filters currently applied."""
        labels = []

        slug = self.request.GET.get('category', '').strip()
        if slug:
            labels.extend(cat.name for cat in categories if cat.slug == slug)

        province = self.request.GET.get('province', '').strip()
        if province:
            labels.extend(label for value, label in EXAM_PROVINCES if value == province)

        year = self.request.GET.get('year', '').strip()
        if year.isdigit():
            labels.append(gettext('year %s') % year)

        return labels

    def get_seo_title(self, categories):
        labels = self.get_active_filter_labels(categories)
        if not labels:
            return gettext('Exam library')
        # e.g. "Đề vào 10 chuyên Tin - Hà Nội - năm 2024 | Thư viện đề thi"
        return '%s | %s' % (' - '.join(labels), gettext('Exam library'))

    def get_meta_description(self, matched):
        return gettext('%(count)d exam statements from informatics olympiads at every level, the Tin hoc '
                       'tre contest, and entrance exams for specialised computer science classes. Each '
                       'comes with the full statement as a PDF and a practice contest graded '
                       'automatically.') % {'count': matched}

    def get_structured_data(self, context, matched):
        build = self.request.build_absolute_uri
        listing = [{
            '@type': 'ListItem',
            'position': index,
            'url': build(exam.get_absolute_url()),
            'name': exam.title,
        } for index, exam in enumerate(context['exams'], start=1)]

        return {
            '@context': 'https://schema.org',
            '@graph': [
                {
                    '@type': 'CollectionPage',
                    'name': context['title'],
                    'description': context['meta_description'],
                    'url': build(self.request.get_full_path()),
                    'inLanguage': 'vi',
                    'publisher': {
                        '@type': 'Organization',
                        'name': PUBLISHER_NAME,
                        'url': PUBLISHER_URL,
                    },
                },
                {
                    '@type': 'BreadcrumbList',
                    'itemListElement': [
                        {
                            '@type': 'ListItem',
                            'position': 1,
                            'name': gettext('Home'),
                            'item': build('/'),
                        },
                        {
                            '@type': 'ListItem',
                            'position': 2,
                            'name': gettext('Exam library'),
                            'item': build(reverse('library_list')),
                        },
                    ],
                },
                {
                    '@type': 'ItemList',
                    'name': context['title'],
                    'numberOfItems': matched,
                    'itemListOrder': 'https://schema.org/ItemListOrderDescending',
                    'itemListElement': listing,
                },
            ],
        }


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
        context['structured_data'] = dump_json_ld(self.get_structured_data())
        return context

    def get_structured_data(self):
        exam = self.object
        build = self.request.build_absolute_uri
        about = [exam.category.name]
        if exam.province:
            about.append(exam.get_province_display())

        payload = {
            '@type': 'LearningResource',
            'name': exam.title,
            'url': build(exam.get_absolute_url()),
            'inLanguage': 'vi',
            'learningResourceType': gettext('Past exam paper'),
            'educationalLevel': exam.category.name,
            'datePublished': exam.publish_on.date().isoformat(),
            'keywords': ', '.join(about),
            'isAccessibleForFree': True,
            'publisher': {
                '@type': 'Organization',
                'name': PUBLISHER_NAME,
                'url': PUBLISHER_URL,
            },
        }
        if exam.year:
            payload['temporalCoverage'] = str(exam.year)
        if exam.pdf_url:
            payload['encodingFormat'] = 'application/pdf'

        return {
            '@context': 'https://schema.org',
            '@graph': [
                payload,
                {
                    '@type': 'BreadcrumbList',
                    'itemListElement': [
                        {
                            '@type': 'ListItem',
                            'position': 1,
                            'name': gettext('Home'),
                            'item': build('/'),
                        },
                        {
                            '@type': 'ListItem',
                            'position': 2,
                            'name': gettext('Exam library'),
                            'item': build(reverse('library_list')),
                        },
                        {
                            '@type': 'ListItem',
                            'position': 3,
                            'name': exam.title,
                            'item': build(exam.get_absolute_url()),
                        },
                    ],
                },
            ],
        }
