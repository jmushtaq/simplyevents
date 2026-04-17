from django.apps import apps
from django.urls import include, path
from django.contrib import admin
from django.conf import settings

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),

    # Homepage
    path('', include('homepage.urls')),

    # The Django admin is not officially supported; expect breakage.
    # Nonetheless, it's often useful for debugging.

    path('admin/', admin.site.urls),

    path('', include(apps.get_app_config('oscar').urls[0])),
]

if settings.DEBUG:
    import debug_toolbar
    from django.conf.urls.static import static
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
