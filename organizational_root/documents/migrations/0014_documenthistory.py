from pathlib import Path

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_submission_history(apps, schema_editor):
    Document = apps.get_model('documents', 'Document')
    DocumentHistory = apps.get_model('documents', 'DocumentHistory')
    OrganizationProfile = apps.get_model('documents', 'OrganizationProfile')

    organizations_by_user = {
        organization.user_id: organization
        for organization in OrganizationProfile.objects.all()
    }

    for document in Document.objects.all():
        organization = organizations_by_user.get(document.user_id)
        if not organization:
            continue

        event_type = 'RESUBMITTED' if document.status == 'RESUBMITTED' else 'SUBMITTED'
        history = DocumentHistory.objects.create(
            organization=organization,
            document=document,
            actor_id=document.user_id,
            event_type=event_type,
            section=document.section,
            title=document.title,
            file_name=Path(document.uploaded_file.name).name if document.uploaded_file else '',
        )
        DocumentHistory.objects.filter(pk=history.pk).update(created_at=document.uploaded_at)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documents', '0013_adminprofile_rank1_forwarding'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('SUBMITTED', 'Submitted'), ('RESUBMITTED', 'Resubmitted'), ('RANK2_EDITED', 'Edited by Rank 2'), ('RANK2_FORWARDED', 'Forwarded to Rank 1')], max_length=20)),
                ('section', models.CharField(choices=[('EXPLANATORY_REPORTS', 'Explanatory Report'), ('REACCREDITATION', 'Reaccreditation'), ('ACCREDITATION', 'Accreditation'), ('ORGANIZATION_EVENTS', 'Organization Events')], max_length=40)),
                ('title', models.CharField(max_length=255)),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='document_history_actions', to=settings.AUTH_USER_MODEL)),
                ('document', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='history_entries', to='documents.document')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='document_history', to='documents.organizationprofile')),
            ],
            options={
                'verbose_name_plural': 'document history',
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.RunPython(backfill_submission_history, migrations.RunPython.noop),
    ]
