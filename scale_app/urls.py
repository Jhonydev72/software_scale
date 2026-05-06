from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/processes/', views.list_processes, name='list_processes'),
    path('api/upload/', views.upload_lci, name='upload_lci'),
    path('api/calculate/', views.calculate_api, name='calculate_api'),
]
