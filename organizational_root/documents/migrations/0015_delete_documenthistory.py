from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0014_documenthistory'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DocumentHistory',
        ),
    ]
