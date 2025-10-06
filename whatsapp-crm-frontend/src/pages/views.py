# whatsappcrm_backend/customer_data/views.py
from rest_framework.views import APIView
from rest_framework import permissions, status
from django.utils import timezone
from datetime import timedelta

from .models import MemberProfile, Payment
from .exports import (
    export_members_to_excel, export_members_to_pdf,
    export_payment_summary_to_excel, export_payment_summary_to_pdf,
    export_givers_list_finance_excel, export_givers_list_finance_pdf,
    export_givers_list_publication_excel, export_givers_list_publication_pdf
)

class ReportGeneratorView(APIView):
    """
    A view to generate and serve various Excel and PDF reports.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        report_type = request.query_params.get('type')
        period = request.query_params.get('period', 'month') # Default to month for relevant reports

        if not report_type:
            return Response({"error": "Report type must be specified."}, status=status.HTTP_400_BAD_REQUEST)

        # --- Member Reports ---
        if report_type == 'all_members_excel':
            return export_members_to_excel(MemberProfile.objects.all())
        if report_type == 'all_members_pdf':
            return export_members_to_pdf(MemberProfile.objects.all())

        # --- Payment-based Reports ---
        now = timezone.now()
        if period == 'week':
            start_date = now - timedelta(days=7)
            period_name = 'last_7_days'
        elif period == 'year':
            start_date = now - timedelta(days=365)
            period_name = 'last_365_days'
        else: # Default to month
            start_date = now - timedelta(days=30)
            period_name = 'last_30_days'

        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')

        # --- Payment Summary Reports ---
        if report_type == 'payment_summary_excel':
            return export_payment_summary_to_excel(payments, period_name)
        if report_type == 'payment_summary_pdf':
            return export_payment_summary_to_pdf(payments, period_name)

        # --- Givers List Reports ---
        # For these, we'll use the current calendar month for consistency with admin actions
        monthly_payments = Payment.objects.filter(
            created_at__gte=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            status='completed'
        )
        
        if report_type == 'givers_finance_excel':
            return export_givers_list_finance_excel(monthly_payments, 'current_month')
        if report_type == 'givers_finance_pdf':
            return export_givers_list_finance_pdf(monthly_payments, 'current_month')
        if report_type == 'givers_publication_excel':
            return export_givers_list_publication_excel(monthly_payments, 'current_month')
        if report_type == 'givers_publication_pdf':
            return export_givers_list_publication_pdf(monthly_payments, 'current_month')

        return Response({"error": "Invalid report type specified."}, status=status.HTTP_400_BAD_REQUEST)
