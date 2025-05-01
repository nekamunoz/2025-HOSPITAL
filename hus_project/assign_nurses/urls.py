from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('assignation/', views.assignation, name='assignation'),
    path('assignation/run_main/', views.run_main, name='run_main'),
]