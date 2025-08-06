# whatsappcrm_backend/church_services/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SermonViewSet

app_name = 'church_services'

router = DefaultRouter()
router.register(r'sermons', SermonViewSet, basename='sermon')

urlpatterns = [
    path('', include(router.urls)),
]