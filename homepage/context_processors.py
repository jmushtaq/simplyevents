from django.conf import settings

def site_url(request):
    return {
        'DJANGO_SETTINGS': settings,
        'DEBUG': settings.DEBUG,
#        'SYSTEM_NAME_SHORT': settings.SYSTEM_NAME_SHORT,
#        'SYSTEM_NAME': settings.SYSTEM_NAME,
#        'PUBLIC_URL': settings.PUBLIC_URL,
#        'SUPPORT_EMAIL': settings.SUPPORT_EMAIL,
#        'DEPOSIT': int(settings.DEPOSIT * 100),
        #'build_tag': settings.BUILD_TAG,
    }
