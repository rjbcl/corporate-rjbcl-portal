# main_system/migrations/000X_add_custom_permissions.py
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('main_system', '0001_initial'),  # Update to your latest migration
    ]

    operations = [
        migrations.AlterModelOptions(
            name='company',
            options={'permissions': [('approve_company', 'Can approve company'), ('soft_delete_company', 'Can soft delete company')]},
        ),
        migrations.AlterModelOptions(
            name='group',
            options={'permissions': [('approve_group', 'Can approve group'), ('soft_delete_group', 'Can soft delete group')]},
        ),
        migrations.AlterModelOptions(
            name='individual',
            options={'permissions': [('approve_individual', 'Can approve individual'), ('soft_delete_individual', 'Can soft delete individual')]},
        ),
    ]