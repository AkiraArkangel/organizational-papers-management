from django.db import migrations, models


def move_accomplished_to_ready_for_printing(apps, schema_editor):
    Document = apps.get_model('documents', 'Document')
    Document.objects.filter(status='ACCOMPLISHED').update(status='READY_FOR_PRINTING')


def move_ready_for_printing_to_accomplished(apps, schema_editor):
    Document = apps.get_model('documents', 'Document')
    Document.objects.filter(status='READY_FOR_PRINTING').update(status='ACCOMPLISHED')


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            move_accomplished_to_ready_for_printing,
            move_ready_for_printing_to_accomplished,
        ),
        migrations.AlterField(
            model_name='document',
            name='status',
            field=models.CharField(
                choices=[
                    ('SUBMITTED', 'Submitted'),
                    ('CORRECTED', 'Corrected'),
                    ('RESUBMITTED', 'Resubmitted'),
                    ('READY_FOR_PRINTING', 'Ready for Printing'),
                ],
                default='SUBMITTED',
                max_length=20,
            ),
        ),
    ]
