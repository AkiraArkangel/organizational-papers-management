from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_admin_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    AdminProfile = apps.get_model('documents', 'AdminProfile')

    for user in User.objects.filter(is_staff=True):
        AdminProfile.objects.get_or_create(user=user, defaults={'rank': 'RANK_1'})


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documents', '0012_organizationprofile_logo'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rank', models.CharField(choices=[('RANK_1', 'Rank 1 Admin'), ('RANK_2', 'Rank 2 Admin')], default='RANK_1', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='document',
            name='forwarded_to_rank1_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='rank1_notification_seen_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='rank2_reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rank2_reviewed_documents', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(create_admin_profiles, migrations.RunPython.noop),
    ]
