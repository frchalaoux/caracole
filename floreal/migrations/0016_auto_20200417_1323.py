# Generated by Django 3.0.4 on 2020-04-17 11:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('floreal', '0015_auto_20200405_1652'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, default=True, null=True, upload_to=''),
        ),
        migrations.AlterField(
            model_name='delivery',
            name='state',
            field=models.CharField(choices=[('A', 'En préparation'), ('B', 'Ouverte'), ('C', 'Admins'), ('D', 'Gelée'), ('E', 'Régularisation'), ('F', 'Terminée')], default='A', max_length=1),
        ),
        migrations.AlterField(
            model_name='subgroup',
            name='extra_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='subgroupstatefordelivery',
            name='state',
            field=models.CharField(choices=[('X', 'Non validé'), ('Y', 'Commande validée'), ('Z', 'Compta validée')], default='X', max_length=1),
        ),
    ]
