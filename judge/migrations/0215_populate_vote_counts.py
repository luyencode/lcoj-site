from django.db import migrations
from django.db.models import Count, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce

def populate_votes(apps, schema_editor):
    Comment = apps.get_model('judge', 'Comment')
    CommentVote = apps.get_model('judge', 'CommentVote')

    # Subquery to count upvotes (score = 1)
    upvotes_qs = CommentVote.objects.filter(
        comment=OuterRef('pk'),
        score=1
    ).values('comment').annotate(
        count=Count('id')
    ).values('count')
    
    # Subquery to count downvotes (score = -1)
    downvotes_qs = CommentVote.objects.filter(
        comment=OuterRef('pk'),
        score=-1
    ).values('comment').annotate(
        count=Count('id')
    ).values('count')

    # Update all comments efficiently
    Comment.objects.update(
        upvotes=Coalesce(Subquery(upvotes_qs, output_field=IntegerField()), 0),
        downvotes=Coalesce(Subquery(downvotes_qs, output_field=IntegerField()), 0)
    )

class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0214_comment_downvotes_comment_upvotes_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_votes),
    ]
