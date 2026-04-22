from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main_system', '0014_companyaccount_remove_company_username_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='reportaccesslog',
            old_name='generator_company',
            new_name='generator',
        ),
    ]