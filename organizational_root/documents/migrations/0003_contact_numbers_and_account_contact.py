from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_missing_account_contacts(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    AccountContact = apps.get_model('documents', 'AccountContact')
    OrganizationProfile = apps.get_model('documents', 'OrganizationProfile')

    for user in User.objects.all():
        if AccountContact.objects.filter(user=user).exists():
            continue

        account_type = 'admin' if user.is_staff else 'organization'
        contact_number = ''

        if account_type == 'organization':
            profile = OrganizationProfile.objects.filter(user=user).first()
            if profile:
                contact_number = profile.contact_number

        AccountContact.objects.create(
            user=user,
            account_type=account_type,
            contact_number=contact_number,
        )


def remove_generated_account_contacts(apps, schema_editor):
    AccountContact = apps.get_model('documents', 'AccountContact')
    AccountContact.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documents', '0002_update_status_choices'),
    ]

    operations = [
        migrations.RenameField(
            model_name='organizationprofile',
            old_name='contact_email',
            new_name='contact_number',
        ),
        migrations.AlterField(
            model_name='organizationprofile',
            name='contact_number',
            field=models.CharField(max_length=30),
        ),
        migrations.CreateModel(
            name='AccountContact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_type', models.CharField(choices=[('organization', 'Organization Account'), ('admin', 'Admin Account')], max_length=20)),
                ('contact_number', models.CharField(max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(
            create_missing_account_contacts,
            remove_generated_account_contacts,
        ),
    ]
