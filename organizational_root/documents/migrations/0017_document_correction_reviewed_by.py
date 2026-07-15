from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documents', '0016_update_file_sections'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='correction_reviewed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='corrected_documents',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
