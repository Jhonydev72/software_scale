from django.urls import path
from . import views

urlpatterns = [
    # Rota da página inicial
    path('', views.index, name='index'),

    # Rotas da API
    path('api/processes/', views.list_processes, name='list_processes'),
    path('api/upload-lci/', views.upload_lci, name='upload_lci'),
    path('api/calculate/', views.calculate_api, name='calculate_api'),

    # Rotas do Dashboard
    path('api/inventories/', views.list_inventories, name='list_inventories'),
    path('api/dashboard/<int:inventory_id>/', views.dashboard_api, name='dashboard_api'),

    # Rota para baixar o modelo da planilha
    path('download-template/', views.download_template, name='download_template'),
]