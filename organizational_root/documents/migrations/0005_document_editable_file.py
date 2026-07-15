from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_remove_contact_info_and_add_status_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='editable_file',
            field=models.FileField(blank=True, null=True, upload_to='editable/'),
        ),
    ]
