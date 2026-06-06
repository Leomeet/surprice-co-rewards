from django.db import migrations


DEFAULT_WA_TEMPLATE = (
    'Hi {name}! You have earned {points} reward points '
    '(purchase of ₹{amount}). Thank you for shopping with us!'
)


def copy_products_and_seed_template(apps, schema_editor):
    OldProduct = apps.get_model('users', 'Product')
    NewProduct = apps.get_model('billing', 'Product')
    WhatsAppTemplate = apps.get_model('billing', 'WhatsAppTemplate')

    for old in OldProduct.objects.all():
        NewProduct.objects.get_or_create(
            name=old.name,
            defaults={'price': '0.00', 'point_value': old.point_value, 'description': ''},
        )

    WhatsAppTemplate.objects.get_or_create(
        pk=1,
        defaults={'body': DEFAULT_WA_TEMPLATE},
    )


def reverse_migration(apps, schema_editor):
    apps.get_model('billing', 'Product').objects.all().delete()
    apps.get_model('billing', 'WhatsAppTemplate').objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
        ('users', '0003_alter_customuser_options'),
    ]

    operations = [
        migrations.RunPython(copy_products_and_seed_template, reverse_migration),
    ]
