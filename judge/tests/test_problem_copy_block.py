from django.test import TestCase
from django.urls import reverse

from judge.models import Problem, ProblemGroup, ProblemType
from judge.models.tests.util import create_user


class ProblemBlockCopyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group = ProblemGroup.objects.create(name='Test Group', full_name='Test Group')
        cls.problem_type = ProblemType.objects.create(name='Test Type')

    def test_block_copy_defaults_to_false(self):
        problem = Problem.objects.create(
            code='testblock',
            name='Test Block Copy',
            time_limit=1,
            memory_limit=65536,
            points=1,
            group=self.group,
        )
        problem.types.add(self.problem_type)
        self.assertFalse(problem.block_copy)

    def test_block_copy_can_be_set_true(self):
        problem = Problem.objects.create(
            code='testblock2',
            name='Test Block Copy 2',
            time_limit=1,
            memory_limit=65536,
            points=1,
            group=self.group,
            block_copy=True,
        )
        problem.types.add(self.problem_type)
        self.assertTrue(problem.block_copy)


class ProblemBlockCopyViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group = ProblemGroup.objects.create(name='Test Group', full_name='Test Group')
        cls.problem_type = ProblemType.objects.create(name='Test Type')
        cls.problem = Problem.objects.create(
            code='viewtest',
            name='View Test',
            time_limit=1,
            memory_limit=65536,
            points=1,
            description='# Hello\n\nThis is a problem description.',
            group=cls.group,
            is_public=True,
            block_copy=True,
        )
        cls.problem.types.add(cls.problem_type)
        cls.student = create_user(username='student')
        cls.staff_user = create_user(username='staff',
                                      is_staff=True,
                                      user_permissions=('change_problem',))

    def test_blocked_user_sees_banner(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('problem_detail', args=('viewtest',)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'block-copy-banner')
        self.assertContains(response, 'user-select: none')

    def test_staff_user_does_not_see_banner(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('problem_detail', args=('viewtest',)))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'block-copy-banner')
        self.assertNotContains(response, 'user-select: none')

    def test_block_copy_false_no_banner(self):
        self.problem.block_copy = False
        self.problem.save()
        self.client.force_login(self.student)
        response = self.client.get(reverse('problem_detail', args=('viewtest',)))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'block-copy-banner')
