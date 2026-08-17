from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from judge.models.contest import Contest
from judge.utils.url import get_absolute_pdf_url

__all__ = ['ExamCategory', 'ExamStatement', 'EXAM_PROVINCES']

EXAM_PROVINCES = (
    ('ha_noi', 'Hà Nội'),
    ('tp_ho_chi_minh', 'TP. Hồ Chí Minh'),
    ('hai_phong', 'Hải Phòng'),
    ('da_nang', 'Đà Nẵng'),
    ('can_tho', 'Cần Thơ'),
    ('an_giang', 'An Giang'),
    ('ba_ria_vung_tau', 'Bà Rịa - Vũng Tàu'),
    ('bac_giang', 'Bắc Giang'),
    ('bac_kan', 'Bắc Kạn'),
    ('bac_lieu', 'Bạc Liêu'),
    ('bac_ninh', 'Bắc Ninh'),
    ('ben_tre', 'Bến Tre'),
    ('binh_dinh', 'Bình Định'),
    ('binh_duong', 'Bình Dương'),
    ('binh_phuoc', 'Bình Phước'),
    ('binh_thuan', 'Bình Thuận'),
    ('ca_mau', 'Cà Mau'),
    ('cao_bang', 'Cao Bằng'),
    ('dak_lak', 'Đắk Lắk'),
    ('dak_nong', 'Đắk Nông'),
    ('dien_bien', 'Điện Biên'),
    ('dong_nai', 'Đồng Nai'),
    ('dong_thap', 'Đồng Tháp'),
    ('gia_lai', 'Gia Lai'),
    ('ha_giang', 'Hà Giang'),
    ('ha_nam', 'Hà Nam'),
    ('ha_tinh', 'Hà Tĩnh'),
    ('hai_duong', 'Hải Dương'),
    ('hau_giang', 'Hậu Giang'),
    ('hoa_binh', 'Hòa Bình'),
    ('hung_yen', 'Hưng Yên'),
    ('khanh_hoa', 'Khánh Hòa'),
    ('kien_giang', 'Kiên Giang'),
    ('kon_tum', 'Kon Tum'),
    ('lai_chau', 'Lai Châu'),
    ('lam_dong', 'Lâm Đồng'),
    ('lang_son', 'Lạng Sơn'),
    ('lao_cai', 'Lào Cai'),
    ('long_an', 'Long An'),
    ('nam_dinh', 'Nam Định'),
    ('nghe_an', 'Nghệ An'),
    ('ninh_binh', 'Ninh Bình'),
    ('ninh_thuan', 'Ninh Thuận'),
    ('phu_tho', 'Phú Thọ'),
    ('phu_yen', 'Phú Yên'),
    ('quang_binh', 'Quảng Bình'),
    ('quang_nam', 'Quảng Nam'),
    ('quang_ngai', 'Quảng Ngãi'),
    ('quang_ninh', 'Quảng Ninh'),
    ('quang_tri', 'Quảng Trị'),
    ('soc_trang', 'Sóc Trăng'),
    ('son_la', 'Sơn La'),
    ('tay_ninh', 'Tây Ninh'),
    ('thai_binh', 'Thái Bình'),
    ('thai_nguyen', 'Thái Nguyên'),
    ('thanh_hoa', 'Thanh Hóa'),
    ('thua_thien_hue', 'Thừa Thiên Huế'),
    ('tien_giang', 'Tiền Giang'),
    ('tra_vinh', 'Trà Vinh'),
    ('tuyen_quang', 'Tuyên Quang'),
    ('vinh_long', 'Vĩnh Long'),
    ('vinh_phuc', 'Vĩnh Phúc'),
    ('yen_bai', 'Yên Bái'),
)


def validate_exam_year(value):
    max_year = timezone.now().year + 1
    if value < 1990 or value > max_year:
        raise ValidationError(_('Exam year must be between 1990 and %d.') % max_year)


class ExamCategory(models.Model):
    name = models.CharField(max_length=40, unique=True, verbose_name=_('name'))
    slug = models.SlugField(max_length=50, unique=True, verbose_name=_('slug'))
    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name=_('order'))

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _('exam category')
        verbose_name_plural = _('exam categories')

    def __str__(self):
        return self.name


class ExamStatement(models.Model):
    title = models.CharField(max_length=100, verbose_name=_('title'))
    slug = models.SlugField(verbose_name=_('slug'))
    category = models.ForeignKey(ExamCategory, related_name='statements',
                                 on_delete=models.PROTECT, verbose_name=_('category'))
    province = models.CharField(max_length=50, choices=EXAM_PROVINCES, blank=True, default='',
                                verbose_name=_('province'))
    year = models.IntegerField(blank=True, null=True, validators=[validate_exam_year],
                               verbose_name=_('year'))
    description = models.TextField(blank=True, verbose_name=_('description'))
    pdf_url = models.CharField(max_length=200, blank=True, default='', verbose_name=_('PDF URL'))
    contest = models.ForeignKey(Contest, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='exam_statements', verbose_name=_('contest'))
    is_visible = models.BooleanField(default=True, verbose_name=_('visible'))
    publish_on = models.DateTimeField(default=timezone.now, verbose_name=_('publish on'))

    class Meta:
        ordering = ['-publish_on']
        verbose_name = _('exam statement')
        verbose_name_plural = _('exam statements')

    def __str__(self):
        return self.title

    @property
    def absolute_pdf_url(self):
        return get_absolute_pdf_url(self.pdf_url) if self.pdf_url else None

    def get_absolute_url(self):
        return reverse('library_detail', args=(self.id, self.slug))
