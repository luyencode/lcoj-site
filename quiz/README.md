# Quiz App

Standalone quiz system: question bank, quizzes with problem-style access control, auto-graded attempts (MC/MA/TF/SA), XLSX/JSON import, per-quiz leaderboard.

## Permissions

- `quiz.edit_all_quiz` - staff: everything.
- `quiz.edit_own_quiz` - teachers: create quizzes/questions, edit own, import/export.

## JSON import format

A list of question objects:

```json
[{
  "type": "MC",
  "title": "short bank name",
  "content": "markdown body",
  "choices": ["a", "b"],
  "correct": 0,
  "points": 1.0,
  "category": "category-slug",
  "level": "easy",
  "explanation": "markdown, shown on result page",
  "shuffle": false,
  "ma_strategy": "all_or_nothing"
}]
```

- MC: `"correct": 0` (0-based index)
- MA: `"correct": [0, 2]`
- TF: `"correct": true`
- SA: `"correct": ["42", {"text": "4[0-9]", "case_sensitive": false, "is_regex": true}]`

## Timer model

No background jobs. `started_at + time_limit` is the deadline; saves past deadline + 30s grace are rejected and the attempt is finalized lazily on the next touch.
