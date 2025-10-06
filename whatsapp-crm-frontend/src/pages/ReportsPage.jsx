import React, { useState } from 'react';
import { toast } from 'sonner';
import { apiCall } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FiFileText, FiGrid, FiDownload, FiLoader, FiUsers, FiDollarSign } from 'react-icons/fi';

const ReportCard = ({ title, description, icon, children }) => (
  <Card className="dark:bg-slate-800 dark:border-slate-700">
    <CardHeader className="flex flex-row items-start gap-4">
      {React.cloneElement(icon, { className: "h-8 w-8 text-blue-500 mt-1" })}
      <div>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </div>
    </CardHeader>
    <CardContent className="space-y-3">
      {children}
    </CardContent>
  </Card>
);

export default function ReportsPage() {
  const [loadingReport, setLoadingReport] = useState(null);
  const [paymentPeriod, setPaymentPeriod] = useState('month');

  const handleDownload = async (reportType, period) => {
    const uniqueReportKey = period ? `${reportType}_${period}` : reportType;
    setLoadingReport(uniqueReportKey);

    try {
      const queryParams = new URLSearchParams({ type: reportType });
      if (period) {
        queryParams.append('period', period);
      }
      
      // We need to handle blob responses from our apiCall utility
      const response = await apiCall(`/crm-api/customer-data/reports/?${queryParams.toString()}`, { method: 'GET', returnRawResponse: true });

      // Extract filename from Content-Disposition header
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `${uniqueReportKey}_report.bin`; // fallback filename
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1];
        }
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      toast.success(`Report "${filename}" downloaded successfully.`);
    } catch (error) {
      toast.error(`Failed to generate report: ${error.message}`);
      console.error("Report download error:", error);
    } finally {
      setLoadingReport(null);
    }
  };

  const DownloadButton = ({ reportType, format, period }) => {
    const key = period ? `${reportType}_${period}` : reportType;
    const isLoading = loadingReport === key;
    const Icon = format === 'excel' ? FiGrid : FiFileText;

    return (
      <Button
        variant="outline"
        className="w-full justify-start dark:text-slate-300 dark:border-slate-600"
        onClick={() => handleDownload(reportType, period)}
        disabled={isLoading}
      >
        {isLoading ? <FiLoader className="animate-spin mr-2 h-4 w-4" /> : <Icon className="mr-2 h-4 w-4" />}
        {isLoading ? `Generating ${format.toUpperCase()}...` : `Download ${format.toUpperCase()}`}
      </Button>
    );
  };

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-center">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2">
            <FiDownload /> Reports
          </h1>
          <p className="text-muted-foreground mt-1">Generate and download data exports.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Member Reports */}
        <ReportCard
          title="Member Reports"
          description="Export details for all church members."
          icon={<FiUsers />}
        >
          <DownloadButton reportType="all_members_excel" format="excel" />
          <DownloadButton reportType="all_members_pdf" format="pdf" />
        </ReportCard>

        {/* Payment Summary */}
        <ReportCard
          title="Payment Summary"
          description="Aggregated totals for different payment types over a selected period."
          icon={<FiDollarSign />}
        >
          <div className="flex items-center gap-3 mb-3">
            <label htmlFor="payment-period" className="text-sm font-medium text-muted-foreground">Period:</label>
            <Select value={paymentPeriod} onValueChange={setPaymentPeriod}>
              <SelectTrigger id="payment-period" className="w-[180px] dark:bg-slate-700">
                <SelectValue placeholder="Select period" />
              </SelectTrigger>
              <SelectContent className="dark:bg-slate-700">
                <SelectItem value="week">Last 7 Days</SelectItem>
                <SelectItem value="month">Last 30 Days</SelectItem>
                <SelectItem value="year">Last 365 Days</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DownloadButton reportType="payment_summary_excel" format="excel" period={paymentPeriod} />
          <DownloadButton reportType="payment_summary_pdf" format="pdf" period={paymentPeriod} />
        </ReportCard>

        {/* Givers List (Finance) */}
        <ReportCard
          title="Givers List (Finance)"
          description="Detailed list of givers and their total contribution for the current month. For internal finance use."
          icon={<FiGrid />}
        >
          <DownloadButton reportType="givers_finance_excel" format="excel" />
          <DownloadButton reportType="givers_finance_pdf" format="pdf" />
        </ReportCard>

        {/* Givers List (Publication) */}
        <ReportCard
          title="Givers List (Publication)"
          description="A simple list of giver names for the current month, suitable for public acknowledgement."
          icon={<FiFileText />}
        >
          <DownloadButton reportType="givers_publication_excel" format="excel" />
          <DownloadButton reportType="givers_publication_pdf" format="pdf" />
        </ReportCard>
      </div>
    </div>
  );
}