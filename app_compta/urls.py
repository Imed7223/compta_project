from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EcritureViewSet, TransactionViewSet
from app_compta.views import dashboard_view
from . import views


router = DefaultRouter()
router.register(r'ecritures', EcritureViewSet)
router.register(r'transactions', TransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', dashboard_view, name='dashboard'),
   path('import-csv/', views.import_csv_view, name='import_csv'),
   path('reset/', views.reset_donnees_view, name='reset_donnees'),
]
