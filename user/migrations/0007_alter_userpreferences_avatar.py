# Generated by Django 5.2.1 on 2025-05-31 22:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0006_userpreferences_avatar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userpreferences',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='avatars/', verbose_name='Foto de perfil'),
        ),
    ]
