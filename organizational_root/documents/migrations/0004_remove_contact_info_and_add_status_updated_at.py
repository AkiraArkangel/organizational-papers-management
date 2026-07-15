from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_contact_numbers_and_account_contact'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accountcontact',
            name='user',
        ),
        migrations.DeleteModel(
            name='AccountContact',
        ),
        migrations.RemoveField(
            model_name='organizationprofile',
            name='contact_number',
        ),
        migrations.AddField(
            model_name='document',
            name='status_updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
