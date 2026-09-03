from django.db import migrations

from bookings.service_catalog import CATEGORIES


def seed_categories(apps, schema_editor):
    """
    Pune categoriile standard, o singură dată.

    `get_or_create` pe slug, deci rularea repetată nu duplică nimic, iar
    dacă medicul redenumește o categorie, migrarea nu i-o schimbă înapoi.
    """
    ServiceCategory = apps.get_model("bookings", "ServiceCategory")

    for slug, name, order in CATEGORIES:
        ServiceCategory.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "order": order,
                "is_active": True,
            },
        )


def remove_categories(apps, schema_editor):
    """
    La dat înapoi, ștergem doar categoriile goale.

    Una care are deja servicii ale medicului rămâne — o migrare inversă
    nu are voie să șteargă date reale.
    """
    ServiceCategory = apps.get_model("bookings", "ServiceCategory")

    slugs = [slug for slug, _name, _order in CATEGORIES]

    ServiceCategory.objects.filter(
        slug__in=slugs,
        services__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0006_servicecategory_alter_service_options_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_categories, remove_categories),
    ]