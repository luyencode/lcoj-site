from django.urls import include, path

from quiz.views import editor, importer, student
from quiz.views.preview import QuizMarkdownPreviewView
from quiz.views.select2 import QuizQuestionSelect2View

urlpatterns = [
    path('/', student.QuizList.as_view(), name='quiz_list'),
    path('/preview', QuizMarkdownPreviewView.as_view(), name='quiz_preview'),
    path('/select2/question', QuizQuestionSelect2View.as_view(), name='quiz_question_select2'),
    path('/questions', include([
        path('/', editor.QuestionBank.as_view(), name='quiz_question_bank'),
        path('/new', editor.QuestionCreate.as_view(), name='quiz_question_create'),
        path('/<int:question>/edit', editor.QuestionEdit.as_view(),
             name='quiz_question_edit'),
    ])),
    path('/import', include([
        path('/', importer.QuizImport.as_view(), name='quiz_import'),
        path('/confirm', importer.QuizImportConfirm.as_view(),
             name='quiz_import_confirm'),
        path('/template', importer.QuizImportTemplate.as_view(),
             name='quiz_import_template'),
    ])),
    path('/export', importer.QuizExport.as_view(), name='quiz_export'),
    path('/new', editor.QuizEdit.as_view(), name='quiz_create'),
    path('/<str:quiz>', include([
        path('', student.QuizDetail.as_view(), name='quiz_detail'),
        path('/start', student.QuizStart.as_view(), name='quiz_start'),
        path('/ranking', student.QuizRanking.as_view(), name='quiz_ranking'),
        path('/edit', editor.QuizEdit.as_view(), name='quiz_edit'),
        path('/attempts', editor.QuizAttempts.as_view(), name='quiz_attempts'),
        path('/attempt/<int:attempt>', include([
            path('', student.QuizTake.as_view(), name='quiz_take'),
            path('/save', student.QuizSaveAnswer.as_view(), name='quiz_save'),
            path('/violation', student.QuizRecordViolation.as_view(), name='quiz_violation'),
            path('/violations', editor.QuizViolationLog.as_view(), name='quiz_violation_log'),
            path('/submit', student.QuizSubmit.as_view(), name='quiz_submit'),
            path('/result', student.QuizResult.as_view(), name='quiz_result'),
        ])),
    ])),
]
