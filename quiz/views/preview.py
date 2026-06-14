from judge.views.preview import MarkdownPreviewView


class QuizMarkdownPreviewView(MarkdownPreviewView):
    template_name = 'quiz/preview.html'
