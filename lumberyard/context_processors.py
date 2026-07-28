from django.conf import settings


def public_contact(request):
    return {
        "public_contact": settings.PUBLIC_CONTACT,
    }
