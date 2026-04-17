# Adding Bootstrap demo website theme to Django-Oscar
https://builder.bootstrapmade.com/demo/Butterfly/index.html

## Unzip the demo theme pack
```
cd ~/Downloads
Unzip Butterfly
mv Butterfly butterfly
```

## Create new app for the new theme
```
cd ~/projects/django-oscar
python sandbox/manage.py startapp homepage

# For later
python manage.py show_urls

```

## Copy assets to new app
```
cd ~/projects/django-oscar/homepage
mkdir static
mkdir -p templates/homepage
cp -pr ~/Downloads/butterfly/assets static/
cp ~/Downloads/butterfly/*.html templates/homepage/
```

## Create a simple Django view
vi views.py
```
from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic


class HomeTestView(generic.ListView):
    ''' http://localhost:8000/home/  '''
    template_name = "homepage/index_hellow_world.html"
    context_object_name = "homepage/index_hello_world.html"

    def get_queryset(self):
        return None


class HomeView(generic.ListView):
    ''' http://localhost:8000/home/  '''
    template_name = "homepage/starter-page.html"
    context_object_name = "homepage/starter-page.html"
    #context_object_name = "homepage/index.html"
    #template_name = "homepage/index.html"

    def get_queryset(self):
        return None

```

## Update templates to use {% static %}
```
<link rel="icon" href="{% static 'assets/img/favicon.png' %}">
<script src="{% static 'assets/vendor/bootstrap/js/bootstrap.bundle.min.js' %}"></script>
```

## Create a simple Django view
vi sandbox/urls.py
```
...
path('home/', include('homepage.urls')),
...
```

## Try ...
http://localhost:8000/home/





python sandbox/manage.py findstatic css/base.css --verbosity 2
```
