# whatsappcrm_backend/customer_data/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'families', views.FamilyViewSet, basename='family')
router.register(r'profiles', views.MemberProfileViewSet, basename='memberprofile')
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'payment-history', views.PaymentHistoryViewSet, basename='paymenthistory')
router.register(r'prayer-requests', views.PrayerRequestViewSet, basename='prayerrequest')

app_name = 'customer_data_api'

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
    # The Paynow IPN webhook is a standalone function-based view, so it's added separately.
    # It's important that this URL is publicly accessible without authentication.
    path('paynow-ipn/', views.paynow_ipn_webhook, name='paynow-ipn-webhook'),
]