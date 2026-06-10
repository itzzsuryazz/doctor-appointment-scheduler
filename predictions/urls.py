from django.urls import path
from . import views

urlpatterns = [
    path('', views.predictions_dashboard, name='predictions_dashboard'),
    path('train/', views.train_model_view, name='train_model'),
    path('bulk-predict/', views.bulk_predict, name='bulk_predict'),
]