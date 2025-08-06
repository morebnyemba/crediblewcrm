import React, { useState, useEffect, useCallback } from 'react';
import { addDays, format } from 'date-fns';
import { toast } from 'sonner';
import { apiCall } from '@/lib/api';

// UI Components
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { DatePickerWithRange } from '@/components/ui/date-range-picker';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from '@/components/ui/skeleton';
import { FiDollarSign, FiUsers, FiMessageSquare, FiHeart, FiBarChart2, FiLoader, FiAlertTriangle } from 'react-icons/fi';

// --- Import Real Chart Components ---
import FinancialTrendChart from '@/components/charts/FinancialTrendChart';
import EngagementTrendChart from '@/components/charts/EngagementTrendChart';
import MessageVolumeChart from '@/components/charts/MessageVolumeChart';
import PrayerRequestChart from '@/components/charts/PrayerRequestChart';

export default function AnalyticsPage() {
    const [dateRange, setDateRange] = useState({
        from: addDays(new Date(), -30),
        to: new Date(),
    });
    const [groupBy, setGroupBy] = useState('day');
    const [prayerGroupBy, setPrayerGroupBy] = useState('day'); // Separate state for prayer chart
    const [isLoading, setIsLoading] = useState(true);
    const [analyticsData, setAnalyticsData] = useState({
        financial: null,
        engagement: null,
        messages: null,
        prayer: null,
    });

    const fetchData = useCallback(async () => {
        setIsLoading(true);
        const startDate = dateRange.from ? format(dateRange.from, 'yyyy-MM-dd') : '';
        const endDate = dateRange.to ? format(dateRange.to, 'yyyy-MM-dd') : '';

        const endpoints = {
            financial: `/crm-api/stats/financial/?start_date=${startDate}&end_date=${endDate}&group_by=${groupBy}`,
            engagement: `/crm-api/stats/engagement/?start_date=${startDate}&end_date=${endDate}&group_by=${groupBy}`,
            messages: `/crm-api/stats/messages/?start_date=${startDate}&end_date=${endDate}&group_by=${groupBy}`,
            // Prayer request endpoint uses its own groupBy state
            prayer: `/crm-api/stats/prayer-requests/?start_date=${startDate}&end_date=${endDate}&group_by=${prayerGroupBy}`,
        };

        const results = await Promise.allSettled(Object.values(endpoints).map(url => apiCall(url)));
        const data = {};
        Object.keys(endpoints).forEach((key, index) => {
            if (results[index].status === 'fulfilled') {
                data[key] = results[index].value;
            } else {
                data[key] = null;
                toast.error(`Failed to load ${key} data.`);
                console.error(`Error fetching ${key} data:`, results[index].reason);
            }
        });
        setAnalyticsData(data);
        setIsLoading(false);
    }, [dateRange, groupBy, prayerGroupBy]); // Add prayerGroupBy to dependency array

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const StatCard = ({ title, value, icon, isLoading }) => (
        <Card className="dark:bg-slate-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
                {icon}
            </CardHeader>
            <CardContent>
                {isLoading ? <Skeleton className="h-8 w-3/4" /> : <div className="text-2xl font-bold">{value}</div>}
            </CardContent>
        </Card>
    );

    return (
        <div className="space-y-8 p-4 md:p-8">
            {/* Header and Filters */}
            <div className="flex flex-wrap justify-between items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold">Detailed Analytics</h1>
                    <p className="text-muted-foreground">Dive deep into your CRM data.</p>
                </div>
                <div className="flex items-center gap-2">
                    <Select value={groupBy} onValueChange={setGroupBy}>
                        <SelectTrigger className="w-[120px]"><SelectValue placeholder="Group by" /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="day">Day</SelectItem>
                            <SelectItem value="week">Week</SelectItem>
                            <SelectItem value="month">Month</SelectItem>
                        </SelectContent>
                    </Select>
                    <DatePickerWithRange date={dateRange} setDate={setDateRange} />
                </div>
            </div>

            {/* Financial Analytics */}
            <section className="space-y-4">
                <h2 className="text-2xl font-semibold flex items-center"><FiDollarSign className="mr-3 text-green-500" />Financial Analytics</h2>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    <StatCard title="Total Giving" value={analyticsData.financial ? `$${Number(analyticsData.financial.summary.total_giving).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '...'} icon={<FiDollarSign className="h-4 w-4 text-muted-foreground" />} isLoading={isLoading} />
                    <StatCard title="Total Transactions" value={analyticsData.financial ? analyticsData.financial.summary.total_transactions.toLocaleString() : '...'} icon={<FiBarChart2 className="h-4 w-4 text-muted-foreground" />} isLoading={isLoading} />
                    <StatCard title="Avg. Transaction Value" value={analyticsData.financial ? `$${Number(analyticsData.financial.summary.average_transaction_value).toFixed(2)}` : '...'} icon={<FiDollarSign className="h-4 w-4 text-muted-foreground" />} isLoading={isLoading} />
                </div>
                <Card><CardHeader><CardTitle>Giving Trends</CardTitle></CardHeader><CardContent className="h-80"><FinancialTrendChart data={analyticsData.financial?.trends} isLoading={isLoading} /></CardContent></Card>
            </section>

            {/* Engagement Analytics */}
            <section className="space-y-4">
                <h2 className="text-2xl font-semibold flex items-center"><FiUsers className="mr-3 text-blue-500" />Engagement Analytics</h2>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    <StatCard title="Active Contacts" value={analyticsData.engagement ? analyticsData.engagement.summary.active_contacts_in_period.toLocaleString() : '...'} icon={<FiUsers className="h-4 w-4 text-muted-foreground" />} isLoading={isLoading} />
                    <StatCard title="Flows Started" value={analyticsData.engagement ? analyticsData.engagement.summary.flows_started_in_period.toLocaleString() : '...'} icon={<FiMessageSquare className="h-4 w-4 text-muted-foreground" />} isLoading={isLoading} />
                    <StatCard title="Handovers Requested" value={analyticsData.engagement ? analyticsData.engagement.summary.handovers_requested_in_period.toLocaleString() : '...'} icon={<FiAlertTriangle className="h-4 w-4 text-muted-foreground" />} isLoading={isLoading} />
                </div>
                <Card><CardHeader><CardTitle>New Contact Trends</CardTitle></CardHeader><CardContent className="h-80"><EngagementTrendChart data={analyticsData.engagement?.new_contacts_trend.data} isLoading={isLoading} /></CardContent></Card>
            </section>
            
            {/* Message Volume */}
            <section className="space-y-4">
                <h2 className="text-2xl font-semibold flex items-center"><FiMessageSquare className="mr-3 text-purple-500" />Message Volume</h2>
                <Card><CardHeader><CardTitle>Incoming vs. Outgoing Messages</CardTitle></CardHeader><CardContent className="h-80"><MessageVolumeChart data={analyticsData.messages?.volume_per_period} isLoading={isLoading} /></CardContent></Card>
            </section>

            {/* Prayer Requests */}
            <section className="space-y-4">
                <div className="flex justify-between items-center">
                    <h2 className="text-2xl font-semibold flex items-center"><FiHeart className="mr-3 text-red-500" />Prayer Requests</h2>
                    <Select value={prayerGroupBy} onValueChange={setPrayerGroupBy}>
                        <SelectTrigger className="w-[180px]"><SelectValue placeholder="Group by" /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="day">By Day</SelectItem>
                            <SelectItem value="week">By Week</SelectItem>
                            <SelectItem value="month">By Month</SelectItem>
                            <SelectItem value="category">By Category</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                 <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    <StatCard title="Total Requests" value={analyticsData.prayer ? analyticsData.prayer.summary.total_requests.toLocaleString() : '...'} icon={<FiHeart className="h-4 w-4 text-muted-foreground" />} isLoading={isLoading} />
                </div>
                <Card><CardHeader><CardTitle>Prayer Request Trends</CardTitle></CardHeader><CardContent className="h-80"><PrayerRequestChart data={analyticsData.prayer?.trends} groupBy={prayerGroupBy} isLoading={isLoading} /></CardContent></Card>
            </section>
        </div>
    );
}