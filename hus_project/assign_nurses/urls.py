from django.urls import path
from .views import assignation

urlpatterns = [
    path('', assignation, name='sign-in')
]