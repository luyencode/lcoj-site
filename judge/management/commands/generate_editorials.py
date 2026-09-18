#!/usr/bin/env python
"""
Django management command to generate editorials using Pydantic structured output.

This version uses Pydantic models to ensure structured, consistent output from the LLM.
"""

import logging
import time
from typing import List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from judge.models import Problem, Solution, Submission

try:
    from pydantic import BaseModel, Field
except ImportError:
    raise CommandError('Pydantic not installed. Run: pip install pydantic')


# ==================== PYDANTIC MODELS FOR STRUCTURED OUTPUT ====================

class Approach(BaseModel):
    """Represents a solution approach."""
    name: str = Field(description='Name of the approach (e.g., "Brute Force", "Hash Map", "Two Pointers")')
    language: str = Field(description='Programming language used')
    code: str = Field(description='Code snippet for this approach')
    time_complexity: str = Field(description='Time complexity in Big-O notation (e.g., "O(n)", "O(n log n)")')
    space_complexity: str = Field(description='Space complexity in Big-O notation (e.g., "O(1)", "O(n)")')
    explanation: str = Field(description='Detailed explanation of how this approach works')


class EditorialContent(BaseModel):
    """Structured editorial content."""
    problem_understanding: str = Field(
        description='Clear explanation of what the problem asks and the key concepts',
    )
    approaches: List[Approach] = Field(
        description='List of solution approaches, from simplest to most optimal',
        min_items=1,
    )
    key_insights: List[str] = Field(
        description='Key insights and patterns to recognize similar problems',
        min_items=1,
    )
    common_pitfalls: List[str] = Field(
        description='Common mistakes and edge cases to watch out for',
        min_items=1,
    )


# ==================== EDITORIAL GENERATOR ====================

class EditorialGenerator:
    """Handles the editorial generation process with structured output."""

    def __init__(self, command, **options):
        self.command = command
        self.dry_run = options.get('dry_run', False)
        self.verbose = options.get('verbose', False)
        self.model = options.get('model', 'mimo-v2-flash')
        self.temperature = options.get('temperature', 0.7)
        self.max_retries = options.get('max_retries', 3)
        self.retry_delay = options.get('retry_delay', 2)

        # Setup logging
        log_file = options.get('log_file')
        self._setup_logging(log_file)

        # OpenAI client (lazy load)
        self._client = None

    @property
    def client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                import os

                base_url = os.environ.get('OPENAI_BASE_URL')
                api_key = os.environ.get('OPENAI_API_KEY')

                if not api_key:
                    raise CommandError(
                        'OPENAI_API_KEY environment variable not set. '
                        'Please set it with: export OPENAI_API_KEY="sk-..."',
                    )

                if base_url:
                    self.logger.info('Using custom OpenAI endpoint: %s', base_url)
                    self._client = OpenAI(
                        base_url=base_url,
                        api_key=api_key,
                    )
                else:
                    self._client = OpenAI(api_key=api_key)

            except ImportError:
                raise CommandError(
                    'OpenAI package not installed. Run: pip install openai',
                )
            except Exception as e:
                raise CommandError(f'Failed to initialize OpenAI client: {e}')
        return self._client

    def _setup_logging(self, log_file=None):
        """Setup logging configuration."""
        handlers = [logging.StreamHandler()]
        if log_file:
            handlers.append(logging.FileHandler(log_file))

        logging.basicConfig(
            level=logging.DEBUG if self.verbose else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers,
        )
        self.logger = logging.getLogger(__name__)

    def get_problems_without_editorials(self, problem_code=None, limit=10, offset=0):
        """Get problems that don't have editorials yet."""
        base_qs = Problem.objects.filter(is_public=True)

        if problem_code:
            base_qs = base_qs.filter(code=problem_code)
        else:
            existing = Solution.objects.values_list('problem_id', flat=True)
            base_qs = base_qs.exclude(id__in=existing)

        return base_qs.order_by('id')[offset:offset + limit]

    def get_ac_solutions(self, problem, limit=3):
        """Get up to 'limit' different AC submissions for a problem (C/C++ only)."""
        ac_submissions = Submission.objects.filter(
            problem=problem,
            result='AC',
            status='D',
            language__name__regex=r'^C*$',  # C, C++, C++17, C++20, C11, etc.
        ).select_related(
            'user', 'user__user', 'language', 'source',
        ).order_by('-id')

        seen = set()
        unique_submissions = []
        for sub in ac_submissions:
            key = (sub.user_id, sub.language_id)
            if key not in seen:
                seen.add(key)
                unique_submissions.append(sub)
                if len(unique_submissions) >= limit:
                    break

        if len(unique_submissions) < limit:
            for sub in ac_submissions:
                if sub.id not in [s.id for s in unique_submissions]:
                    unique_submissions.append(sub)
                    if len(unique_submissions) >= limit:
                        break

        return unique_submissions

    def validate_generation(self, problem, solutions):
        """Validate that we can generate an editorial for this problem."""
        errors = []

        if not problem:
            errors.append('Problem is None')
            return errors

        if not problem.is_public:
            errors.append(f'Problem {problem.code} is not public')

        if Solution.objects.filter(problem=problem).exists():
            errors.append(f'Editorial already exists for {problem.code}')

        if len(solutions) < 1:
            errors.append(f'Insufficient AC C/C++ solutions for {problem.code}: {len(solutions)} (need at least 1)')

        for i, sub in enumerate(solutions):
            if not hasattr(sub, 'source') or not sub.source:
                errors.append(f'Submission {sub.id} has no source code')
                continue

            source_code = sub.source.source
            if not source_code or len(source_code.strip()) < 10:
                errors.append(f'Submission {sub.id} source code too short')

        return errors

    def format_solutions_for_prompt(self, solutions):
        """Format solutions for OpenAI prompt."""
        formatted = []
        for i, sub in enumerate(solutions, 1):
            language = sub.language.common_name if sub.language else 'Unknown'
            username = sub.user.user.username if sub.user and sub.user.user else 'Unknown'
            source = sub.source.source if sub.source else 'No source'

            if len(source) > 1000:
                source = source[:1000] + '\n// ... (truncated)'

            # Normalize language codes for code blocks
            lang_code = language.lower().replace('c++', 'cpp').replace('c#', 'csharp')

            formatted.append(
                f'--- Solution {i} ---\n'
                f'Language: {language}\n'
                f'User: {username}\n'
                f'Submission ID: {sub.id}\n'
                f'Code:\n```{lang_code}\n{source}\n```\n',
            )

        return '\n'.join(formatted)

    def build_openai_prompt(self, problem, formatted_solutions):
        """Build the prompt for OpenAI with structured output requirements."""
        description = problem.description or 'No description available'

        prompt = (
            f'You are an expert in competitive programming education. '
            f'Analyze the problem and solutions, then generate a detailed editorial in Vietnamese.\n\n'
            f'## Problem Information\n'
            f'**Code**: {problem.code}\n'
            f'**Name**: {problem.name}\n'
            f'**Description**: {description}\n\n'
            f'## Accepted Solutions\n'
            f'{formatted_solutions}\n\n'
            f'## Instructions\n'
            f'Analyze the solutions above and create structured editorial data:\n'
            f'1. Explain the problem clearly in Vietnamese\n'
            f'2. Identify 2-3 different approaches from the solutions\n'
            f'3. Order from simplest to most optimal\n'
            f'4. Provide code, complexity, and explanation for each approach\n'
            f'5. List key insights and common pitfalls\n\n'
            f'## Output Requirements\n'
            f'You MUST return valid JSON following this schema:\n'
            f'{{\n'
            f'  "problem_understanding": "string - clear explanation in Vietnamese",\n'
            f'  "approaches": [\n'
            f'    {{\n'
            f'      "name": "string - approach name (e.g., \'Brute Force\', \'Hash Map\')",\n'
            f'      "language": "string - programming language (lowercase, use \'cpp\' for C++, \'csharp\' for C#)",\n'
            f'      "code": "string - code snippet",\n'
            f'      "time_complexity": "string - e.g., O(n), O(n log n), can use ~10^9~ if needed",\n'
            f'      "space_complexity": "string - e.g., O(1), O(n), can use ~10^9~ if needed",\n'
            f'      "explanation": "string - detailed explanation in Vietnamese"\n'
            f'    }}\n'
            f'  ],\n'
            f'  "key_insights": ["string - insight 1", "string - insight 2"],\n'
            f'  "common_pitfalls": ["string - pitfall 1", "string - pitfall 2"]\n'
            f'}}\n\n'
            f'DO NOT include any text outside the JSON object.\n'
        )
        return prompt

    def call_openai_structured(self, prompt, attempt=0):
        """Call OpenAI API with structured output using Pydantic parsing."""
        try:
            # Use the parse method with Pydantic model for structured output
            response = self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a competitive programming education expert. Always return valid JSON.',
                    },
                    {'role': 'user', 'content': prompt},
                ],
                temperature=self.temperature,
                response_format=EditorialContent,
            )

            # Get the parsed result directly
            editorial = response.choices[0].message.parsed
            return editorial

        except Exception as e:
            if attempt < self.max_retries:
                wait_time = self.retry_delay * (2 ** attempt)
                err_msg = str(e)
                self.logger.warning('API error (attempt %d/%d): %s', attempt + 1, self.max_retries, err_msg)
                self.logger.info('Retrying in %d seconds...', wait_time)
                time.sleep(wait_time)
                return self.call_openai_structured(prompt, attempt + 1)
            else:
                raise

    def generate_editorial_content(self, problem, solutions):
        """Generate editorial content using OpenAI with structured output."""
        self.logger.info('Generating editorial for %s...', problem.code)

        formatted_solutions = self.format_solutions_for_prompt(solutions)
        prompt = self.build_openai_prompt(problem, formatted_solutions)

        if self.verbose:
            self.logger.debug('Prompt length: %d characters', len(prompt))

        editorial = self.call_openai_structured(prompt)

        if self.verbose:
            self.logger.debug('Generated structured editorial')

        return editorial

    def format_editorial_to_markdown(self, editorial: EditorialContent, problem):
        """Convert Pydantic EditorialContent to markdown format with Vietnamese headers."""
        lines = []
        # lines.append(f"# Editorial for {problem.code}: {problem.name}")
        lines.append('')
        lines.append('## Hiểu bài toán')
        lines.append(editorial.problem_understanding)
        lines.append('')
        lines.append('## Các cách tiếp cận')

        for i, approach in enumerate(editorial.approaches, 1):
            # Normalize language code
            lang_code = approach.language.lower().replace('c++', 'cpp').replace('c#', 'csharp')

            lines.append(f'### Cách {approach.name}')
            lines.append('')
            lines.append(f'```{lang_code}')
            lines.append(approach.code)
            lines.append('```')
            lines.append('')
            lines.append(f'* **Time Complexity**: {approach.time_complexity}')
            lines.append(f'* **Space Complexity**: {approach.space_complexity}')
            lines.append('')
            lines.append(approach.explanation)
            lines.append('')

        lines.append('## Phân tích độ phức tạp')
        lines.append('| Cách tiếp cận | Time | Space | Tên |')
        lines.append('|--------------|------|-------|-----|')
        for i, approach in enumerate(editorial.approaches, 1):
            lines.append(f'| {i} | {approach.time_complexity} | {approach.space_complexity} | {approach.name} |')
        lines.append('')

        lines.append('## Bài học kinh nghiệm')
        for insight in editorial.key_insights:
            lines.append(f'- {insight}')
        lines.append('')

        lines.append('## Lỗi thường gặp')
        for pitfall in editorial.common_pitfalls:
            lines.append(f'- {pitfall}')

        return '\n'.join(lines)

    def save_editorial(self, problem, editorial: EditorialContent, solutions, dry_run=False):
        """Save editorial to database."""
        content = self.format_editorial_to_markdown(editorial, problem)

        if dry_run:
            self.logger.info('[DRY RUN] Would create editorial for %s', problem.code)
            self.logger.info('Content preview:\n%s...', content[:500])
            return None

        # Get admin user as first author
        from django.contrib.auth.models import User
        try:
            admin_user = User.objects.get(username='admin')
            admin_profile = admin_user.profile
        except User.DoesNotExist:
            # Fallback: get any superuser
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                admin_profile = admin_user.profile
            else:
                # If no admin exists, use first user
                admin_user = User.objects.first()
                admin_profile = admin_user.profile if admin_user else None

        # Get solution authors
        solution_authors = list(set(s.user for s in solutions if s.user))

        # Combine: admin first, then solution authors (without duplicates)
        authors = []
        if admin_profile:
            authors.append(admin_profile)
        for author in solution_authors:
            if author not in authors:
                authors.append(author)

        try:
            with transaction.atomic():
                Solution.objects.filter(problem=problem).delete()

                solution = Solution.objects.create(
                    problem=problem,
                    content=content,
                    is_public=True,
                    publish_on=timezone.now(),
                )

                for author in authors:
                    solution.authors.add(author)

                solution.save()

                self.logger.info('✓ Created editorial for %s (ID: %s)', problem.code, solution.id)
                self.logger.info('  - Authors: %s', ', '.join(a.user.username for a in authors))
                self.logger.info('  - Status: Public')
                self.logger.info('  - Content: %d chars, %d approaches', len(content), len(editorial.approaches))

                return solution

        except Exception:
            self.logger.exception('✗ Failed to save editorial for %s', problem.code)
            raise

    def process_problem(self, problem):
        """Process a single problem."""
        self.logger.info('\n%s', '=' * 60)
        self.logger.info('Processing: %s - %s', problem.code, problem.name)
        self.logger.info('=' * 60)

        solutions = self.get_ac_solutions(problem, limit=3)
        self.logger.info('Found %d AC solutions', len(solutions))

        for i, sub in enumerate(solutions, 1):
            lang = sub.language.common_name if sub.language else 'Unknown'
            user = sub.user.user.username if sub.user and sub.user.user else 'Unknown'
            self.logger.info('  %d. %s by %s (ID: %s)', i, lang, user, sub.id)

        errors = self.validate_generation(problem, solutions)
        if errors:
            self.logger.warning('✗ Validation failed for %s:', problem.code)
            for error in errors:
                self.logger.warning('  - %s', error)
            return False

        try:
            editorial = self.generate_editorial_content(problem, solutions)
            result = self.save_editorial(problem, editorial, solutions, self.dry_run)

            if self.dry_run:
                self.logger.info('✓ Dry run successful: %s', problem.code)
                return True
            elif result:
                self.logger.info('✓ Success: %s', problem.code)
                return True
            else:
                return False

        except Exception:
            self.logger.exception('✗ Failed to generate editorial for %s', problem.code)
            return False


class Command(BaseCommand):
    help = 'Generate editorials for problems using Pydantic structured output'

    def add_arguments(self, parser):
        parser.add_argument('--problem', '-p', help='Process single problem by code')
        parser.add_argument('--limit', '-l', type=int, default=10, help='Max problems to process')
        parser.add_argument('--offset', type=int, default=0, help='Start offset')
        parser.add_argument('--dry-run', action='store_true', default=False, help='Preview mode')
        parser.add_argument('--verbose', action='store_true', default=False, help='Verbose output')
        parser.add_argument('--model', default='mimo-v2-flash', help='OpenAI model')
        parser.add_argument('--temperature', type=float, default=0.7, help='Creativity')
        parser.add_argument('--max-retries', type=int, default=3, help='API retries')
        parser.add_argument('--retry-delay', type=int, default=2, help='Retry delay')
        parser.add_argument('--log-file', help='Log file path')

    def handle(self, *args, **options):
        import os
        if not os.environ.get('OPENAI_API_KEY'):
            self.stdout.write(self.style.WARNING(
                'WARNING: OPENAI_API_KEY not set. Set with: export OPENAI_API_KEY="sk-..."\n',
            ))

        generator = EditorialGenerator(self, **options)

        if options['problem']:
            problems = generator.get_problems_without_editorials(
                problem_code=options['problem'],
                limit=1,
                offset=0,
            )
            if not problems:
                self.stdout.write(self.style.ERROR(
                    f'Problem \'{options["problem"]}\' not found or already has editorial',
                ))
                return
        else:
            problems = generator.get_problems_without_editorials(
                limit=options['limit'],
                offset=options['offset'],
            )

        if not problems:
            self.stdout.write(self.style.NOTICE('No problems found to process.'))
            return

        self.stdout.write(
            self.style.SUCCESS(f'Found {len(problems)} problem(s) to process\n'),
        )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE ==='))
            self.stdout.write('No changes will be saved to database\n')

        results = {'success': 0, 'failed': 0, 'skipped': 0}

        for problem in problems:
            try:
                success = generator.process_problem(problem)
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
            except Exception:
                generator.logger.exception('Unexpected error processing %s', problem.code)
                results['failed'] += 1

        self.stdout.write('\n' + '=' * 60)
