# whatsappcrm_backend/church_services/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SermonViewSet, EventViewSet, MinistryViewSet

app_name = 'church_services'

router = DefaultRouter()
router.register(r'sermons', SermonViewSet, basename='sermon')
router.register(r'events', EventViewSet, basename='event')
router.register(r'ministries', MinistryViewSet, basename='ministry')

urlpatterns = [
    path('', include(router.urls)),
]