from django.core.management.base import BaseCommand

from judge.models import ProblemGroup, ProblemType


# ── Problem Groups (Nhóm bài) ──────────────────────────────────────────────
# These are algorithmic domains, NOT programming languages.
# A problem can be solved in any language, so categories describe the concept.

PROBLEM_GROUPS = [
    # (name, full_name)
    ('co-ban', 'Cơ bản'),
    ('ctdl', 'Cấu trúc dữ liệu'),
    ('do-thi', 'Lý thuyết đồ thị'),
    ('sap-xep-tim-kiem', 'Sắp xếp & Tìm kiếm'),
    ('de-quy-quay-lui', 'Đệ quy & Quay lui'),
    ('chia-de-tri', 'Chia để trị'),
    ('quy-hoach-dong', 'Quy hoạch động'),
    ('tham-lam', 'Tham lam'),
    ('xu-ly-chuoi', 'Xử lý chuỗi'),
    ('xu-ly-bit', 'Xử lý bit'),
    ('toan-hoc', 'Toán học'),
    ('ky-thuat-nang-cao', 'Kỹ thuật nâng cao'),
    ('xu-ly-du-lieu', 'Xử lý dữ liệu & AI cơ bản'),
]

# ── Problem Types (Dạng đề) ────────────────────────────────────────────────
# Finer-grained tags. A problem can have multiple types.
# No language-specific types — these describe algorithmic techniques.

PROBLEM_TYPES = [
    # Fundamentals
    ('bien-kieu-du-lieu', 'Biến & Kiểu dữ liệu'),
    ('nhap-xuat', 'Nhập / Xuất dữ liệu'),
    ('renhanh', 'Câu lệnh rẽ nhánh'),
    ('vong-lap', 'Vòng lặp'),
    ('ham', 'Hàm & Thủ tục'),
    ('dem-tinh-tong', 'Đếm & Tính tổng'),
    ('so-sanh-phan-loai', 'So sánh & Phân loại'),
    ('ep-kieu-bieu-thuc', 'Ép kiểu & Tính biểu thức'),
    ('dieu-kien-thuc-te', 'Điều kiện thực tế'),
    ('in-hinh-day-so', 'In hình & Dãy số'),

    # Arrays & Matrix
    ('mang-1-chieu', 'Mảng một chiều'),
    ('mang-2-chieu', 'Mảng hai chiều'),
    ('bien-doi-mang', 'Biến đổi mảng'),
    ('duong-cheo', 'Đường chéo & Biến đổi ma trận'),
    ('day-con-tien-to', 'Dãy con / Tiền tố'),

    # Strings
    ('chuoi', 'Xử lý chuỗi'),
    ('tim-kiem-tren-xau', 'Tìm kiếm trên xâu'),

    # Data Structures
    ('dslk', 'Danh sách liên kết'),
    ('stack-queue', 'Stack & Queue'),
    ('cay', 'Cây (Tree)'),
    ('bang-bam', 'Bảng băm (Hash Table)'),
    ('heap', 'Heap / Hàng đợi ưu tiên'),
    ('do-thi', 'Đồ thị'),
    ('dem-tan-suat', 'Đếm tần suất'),

    # Graph algorithms
    ('bfs', 'BFS (Tìm kiếm theo chiều rộng)'),
    ('dfs', 'DFS (Tìm kiếm theo chiều sâu)'),
    ('duong-di-ngan-nhat', 'Đường đi ngắn nhất'),
    ('cay-khung', 'Cây khung & Chu trình'),

    # Algorithm techniques
    ('tim-kiem', 'Tìm kiếm'),
    ('chat-nhi-phan', 'Chặt nhị phân kết quả'),
    ('sap-xep', 'Sắp xếp'),
    ('de-quy', 'Đệ quy'),
    ('quay-lui', 'Quay lui'),
    ('chia-de-tri', 'Chia để trị'),
    ('hai-con-tro', 'Hai con trỏ'),
    ('tham-lam', 'Tham lam'),
    ('chon-sap-lich', 'Chọn & Sắp lịch'),
    ('qhd', 'Quy hoạch động'),
    ('xu-ly-bit', 'Xử lý bit'),

    # Math
    ('so-hoc', 'Số học'),
    ('he-co-so-chu-so', 'Hệ cơ số & Chữ số'),
    ('luy-thua-dong-du', 'Lũy thừa & Đồng dư'),
    ('to-hop', 'Tổ hợp'),
    ('hinh-hoc', 'Hình học'),

    # Data Science / AI basics
    ('thong-ke-mo-ta', 'Thống kê mô tả'),
    ('lam-sach-du-lieu', 'Làm sạch & Biến đổi dữ liệu'),
    ('ma-tran-hoc-may', 'Ma trận & Học máy cơ bản'),
]


class Command(BaseCommand):
    help = 'Seed ProblemGroup and ProblemType tables with algorithm-focused taxonomy'

    def handle(self, *args, **options):
        # ── Seed ──────────────────────────────────────────────────────

        groups_created = 0
        groups_existing = 0
        for name, full_name in PROBLEM_GROUPS:
            _, created = ProblemGroup.objects.update_or_create(
                name=name, defaults={'full_name': full_name},
            )
            if created:
                groups_created += 1
                self.stdout.write(self.style.SUCCESS(f'  + Nhóm bài: {full_name}'))
            else:
                groups_existing += 1
                self.stdout.write(f'  = Nhóm bài: {full_name} (đã tồn tại)')

        self.stdout.write(f'\nNhóm bài: {groups_created} mới, {groups_existing} đã tồn tại')

        types_created = 0
        types_existing = 0
        for name, full_name in PROBLEM_TYPES:
            _, created = ProblemType.objects.update_or_create(
                name=name, defaults={'full_name': full_name},
            )
            if created:
                types_created += 1
                self.stdout.write(self.style.SUCCESS(f'  + Dạng đề: {full_name}'))
            else:
                types_existing += 1
                self.stdout.write(f'  = Dạng đề: {full_name} (đã tồn tại)')

        self.stdout.write(f'\nDạng đề: {types_created} mới, {types_existing} đã tồn tại')

        # ── Cleanup ───────────────────────────────────────────────────
        # Remove entries that are no longer in the desired taxonomy.
        # Only delete if no problem references them, to avoid data loss.

        group_names = {g[0] for g in PROBLEM_GROUPS}
        type_names = {t[0] for t in PROBLEM_TYPES}

        for g in ProblemGroup.objects.exclude(name='Uncategorized'):
            if g.name not in group_names:
                problem_count = g.problem_set.count()
                if problem_count == 0:
                    self.stdout.write(self.style.WARNING(
                        f'  - Xoá nhóm bài cũ: {g.full_name} (không có bài nào)'
                    ))
                    g.delete()
                else:
                    self.stdout.write(self.style.NOTICE(
                        f'  ! Giữ nhóm bài cũ: {g.full_name} (đang có {problem_count} bài)'
                    ))

        for t in ProblemType.objects.exclude(name='uncategorized'):
            if t.name not in type_names:
                problem_count = t.problem_set.count()
                if problem_count == 0:
                    self.stdout.write(self.style.WARNING(
                        f'  - Xoá dạng đề cũ: {t.full_name} (không có bài nào)'
                    ))
                    t.delete()
                else:
                    self.stdout.write(self.style.NOTICE(
                        f'  ! Giữ dạng đề cũ: {t.full_name} (đang có {problem_count} bài)'
                    ))

        self.stdout.write(self.style.SUCCESS(
            f'\nHoàn tất: {ProblemGroup.objects.count()} nhóm bài, '
            f'{ProblemType.objects.count()} dạng đề'
        ))
