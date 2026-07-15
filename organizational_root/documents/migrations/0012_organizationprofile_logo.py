from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0011_notification_and_photo_timestamps'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationprofile',
            name='logo',
            field=models.FileField(blank=True, null=True, upload_to='organization_logos/'),
        ),
        migrations.AddField(
            model_name='organizationprofile',
            name='logo_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
