from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0005_document_editable_file'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='document',
            name='editable_file',
        ),
        migrations.AddField(
            model_name='document',
            name='correction_notes',
            field=models.TextField(blank=True),
        ),
    ]
