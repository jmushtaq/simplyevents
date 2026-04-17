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
#    template_name = "homepage/starter-page.html"
#    context_object_name = "homepage/starter-page.html"
    context_object_name = "homepage/index.html"
    template_name = "homepage/index.html"

    def get_queryset(self):
        return None
