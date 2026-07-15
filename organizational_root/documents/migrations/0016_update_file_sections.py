from django.db import migrations, models


COMBINED_SECTION = 'ACCREDITATION_REACCREDITATION'
COMBINED_TITLE = 'ACCREDITATION AND REACCREDITATION'


def merge_sections(apps, schema_editor):
    Document = apps.get_model('documents', 'Document')
    FileSectionTemplate = apps.get_model('documents', 'FileSectionTemplate')

    Document.objects.filter(section__in=['ACCREDITATION', 'REACCREDITATION']).update(
        section=COMBINED_SECTION,
        title=COMBINED_TITLE,
    )

    accreditation_template = FileSectionTemplate.objects.filter(section='ACCREDITATION').first()
    reaccreditation_templates = FileSectionTemplate.objects.filter(section='REACCREDITATION')

    if accreditation_template:
        accreditation_template.section = COMBINED_SECTION
        accreditation_template.save(update_fields=['section'])
        reaccreditation_templates.delete()
    else:
        template = reaccreditation_templates.first()
        if template:
            template.section = COMBINED_SECTION
            template.save(update_fields=['section'])
            reaccreditation_templates.exclude(pk=template.pk).delete()


def restore_sections(apps, schema_editor):
    Document = apps.get_model('documents', 'Document')
    FileSectionTemplate = apps.get_model('documents', 'FileSectionTemplate')

    Document.objects.filter(section=COMBINED_SECTION).update(
        section='ACCREDITATION',
        title='Accreditation',
    )
    FileSectionTemplate.objects.filter(section=COMBINED_SECTION).update(section='ACCREDITATION')


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0015_delete_documenthistory'),
    ]

    operations = [
        migrations.RunPython(merge_sections, restore_sections),
        migrations.AlterField(
            model_name='document',
            name='section',
            field=models.CharField(
                choices=[
                    ('EXPLANATORY_REPORTS', 'EXPLANATORY REPORT'),
                    ('ACCREDITATION_REACCREDITATION', 'ACCREDITATION AND REACCREDITATION'),
                    ('ACCOMPLISHMENT_REPORT', 'ACCOMPLISHMENT REPORT'),
                    ('ORGANIZATION_EVENTS', 'ORGANIZATION EVENTS'),
                ],
                default='EXPLANATORY_REPORTS',
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name='filesectiontemplate',
            name='section',
            field=models.CharField(
                choices=[
                    ('EXPLANATORY_REPORTS', 'EXPLANATORY REPORT'),
                    ('ACCREDITATION_REACCREDITATION', 'ACCREDITATION AND REACCREDITATION'),
                    ('ACCOMPLISHMENT_REPORT', 'ACCOMPLISHMENT REPORT'),
                    ('ORGANIZATION_EVENTS', 'ORGANIZATION EVENTS'),
                ],
                max_length=40,
                unique=True,
            ),
        ),
    ]
