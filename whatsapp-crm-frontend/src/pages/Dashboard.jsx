// Filename: src/pages/Dashboard.jsx
// Main dashboard page - Enhanced with dynamic data fetching, chart integration, and robustness improvements

import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FiBarChart2, FiActivity, FiAlertCircle,
  FiCheckCircle, FiCpu, FiList, FiLoader
} from 'react-icons/fi';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useDashboardData } from '@/hooks/useDashboardData';
import { useAuth } from '@/context/AuthContext';

// --- Import your chart components ---
// Ensure these files exist and export components correctly
import ConversationTrendChart from '@/components/charts/ConversationTrendChat';
import BotPerformanceDisplay from '@/components/charts/BotPerfomanceDisplay';

const getCardStyles = (colorScheme) => {
  switch (colorScheme) {
    case "green": return { bgColor: "bg-green-50 dark:bg-green-900/40", borderColor: "border-green-500/60 dark:border-green-600", textColor: "text-green-700 dark:text-green-300", iconColor: "text-green-600 dark:text-green-400" };
    case "emerald": return { bgColor: "bg-emerald-50 dark:bg-emerald-900/40", borderColor: "border-emerald-500/60 dark:border-emerald-600", textColor: "text-emerald-700 dark:text-emerald-300", iconColor: "text-emerald-600 dark:text-emerald-400" };
    case "lime": return { bgColor: "bg-lime-50 dark:bg-lime-900/40", borderColor: "border-lime-500/60 dark:border-lime-600", textColor: "text-lime-700 dark:text-lime-300", iconColor: "text-lime-600 dark:text-lime-400" };
    case "teal": return { bgColor: "bg-teal-50 dark:bg-teal-900/40", borderColor: "border-teal-500/60 dark:border-teal-600", textColor: "text-teal-700 dark:text-teal-300", iconColor: "text-teal-600 dark:text-teal-400" };
    case "red": return { bgColor: "bg-red-50 dark:bg-red-900/40", borderColor: "border-red-500/60 dark:border-red-600", textColor: "text-red-700 dark:text-red-300", iconColor: "text-red-600 dark:text-red-400" };
    default: return { bgColor: "bg-gray-50 dark:bg-gray-900/40", borderColor: "border-gray-500/60 dark:border-gray-600", textColor: "text-gray-700 dark:text-gray-300", iconColor: "text-gray-600 dark:text-gray-400" };
  }
};

export default function Dashboard() {
  const {
    statsCardsData,
    recentActivities,
    flowInsights,
    conversationTrendsData,
    botPerformanceData,
    systemStatus,
    isLoading,
    error,
  } = useDashboardData();
  const { user } = useAuth(); // Consume auth state with the Jotai-powered hook

  const navigate = useNavigate();

  const CardLinkWrapper = ({ linkTo, children, className }) => {
    const baseClasses = "block h-full";
    if (linkTo) { return <Link to={linkTo} className={`${baseClasses} hover:shadow-2xl transition-shadow duration-300 ${className || ''}`}>{children}</Link>; }
    return <div className={`${baseClasses} ${className || ''}`}>{children}</div>;
  };

  return (
    <div className="space-y-6 md:space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-center gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-800 dark:text-gray-100">Dashboard Overview</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Welcome, {user?.username || 'User'}! Here's a real-time summary of your CRM activity.
          </p>
        </div>
        <div className={`flex items-center gap-2 py-1.5 px-3 rounded-full text-xs font-medium ${systemStatus.color}`}>
          {systemStatus.icon && React.isValidElement(systemStatus.icon) ? React.cloneElement(systemStatus.icon, { className: "h-4 w-4"}) : <FiActivity className="h-4 w-4"/>}
          <span>System: {systemStatus.status}</span>
        </div>
      </div>

      {error && (
        <Card className="border-orange-500/70 dark:border-orange-600/70 bg-orange-50 dark:bg-orange-900/20">
            <CardContent className="p-4 text-sm text-orange-700 dark:text-orange-300 flex items-center gap-3">
                <FiAlertCircle className="h-6 w-6 flex-shrink-0"/>
                <div><span className="font-semibold">Data Loading Issue(s):</span> {error.replace(/\(toasted\)/gi, '').replace(/;/g, '; ')} Some data might be unavailable.</div>
            </CardContent>
        </Card>
      )}

      {/* Stats Cards Grid */}
      <div className="grid grid-cols-1 gap-4 md:gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {isLoading
          ? [...Array(5)].map((_, i) => (
              <Card key={i} className="p-4 sm:p-5 rounded-xl shadow-lg border-l-4 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 flex flex-col justify-between min-h-[140px] md:min-h-[150px]">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <Skeleton className="h-4 w-2/3 dark:bg-slate-700" />
                    <Skeleton className="h-6 w-6 rounded-full dark:bg-slate-700" />
                  </div>
                  <Skeleton className="h-9 w-1/2 mt-2 dark:bg-slate-600" />
                </div>
                <Skeleton className="h-3 w-3/4 mt-2 dark:bg-slate-700" />
              </Card>
            ))
          : statsCardsData.map((stat) => {
              const styles = getCardStyles(stat.colorScheme);
              const defaultIconElement = React.isValidElement(stat.defaultIcon) ? stat.defaultIcon : <FiActivity />;
              return (
                <CardLinkWrapper linkTo={stat.linkTo} key={stat.id}>
                  <div className={`p-4 sm:p-5 rounded-xl shadow-lg border-l-4 ${styles.borderColor} ${styles.bgColor} flex flex-col justify-between min-h-[140px] md:min-h-[150px] h-full transition-transform hover:scale-[1.02] ${stat.linkTo ? 'cursor-pointer' : ''}`}>
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <h3 className="text-xs sm:text-sm font-semibold text-gray-600 dark:text-gray-300 truncate" title={stat.title}>{stat.title}</h3>
                        {React.cloneElement(defaultIconElement, {className: `h-6 w-6 opacity-70 ${styles.iconColor}`})}
                      </div>
                      <p className={`text-2xl sm:text-3xl md:text-4xl font-bold ${styles.textColor}`}>{stat.value}{stat.valueSuffix}</p>
                    </div>
                    {stat.trend && (
                      <div className={`text-xs mt-1.5 ${stat.trendType === 'positive' ? 'text-green-600 dark:text-green-400' : stat.trendType === 'negative' ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400'}`}>
                        {stat.trend}
                      </div>
                    )}
                  </div>
                </CardLinkWrapper>
              );
            })}
      </div>

      {/* Flow Insights & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 md:gap-8">
        <Card className="lg:col-span-1 dark:bg-slate-800 dark:border-slate-700 shadow-lg">
          <CardHeader><CardTitle className="text-lg font-semibold dark:text-slate-100 flex items-center"><FiZap className="mr-2 text-purple-500"/>Flow Insights</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: "Active Flows", value: flowInsights.activeFlows, icon: <FiZap className="text-purple-500"/>, link: "/flows", loading: isLoading },
              { label: "Completions Today", value: flowInsights.completedToday, icon: <FiCheckCircle className="text-emerald-500"/>, link: null, loading: isLoading },
              { label: "Avg. Steps/Flow", value: flowInsights.avgSteps, icon: <FiList className="text-teal-500"/>, link: null, loading: isLoading },
            ].map(item => (
              <div key={item.label} className={`flex justify-between items-center p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50 ${item.link ? 'hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer' : ''} transition-colors`}
                   onClick={item.link && !item.loading ? () => navigate(item.link) : undefined}
              >
                <div className="flex items-center">
                  {React.isValidElement(item.icon) ? React.cloneElement(item.icon, {className: "h-5 w-5 mr-3 opacity-90"}) : <FiActivity className="h-5 w-5 mr-3 opacity-90"/>}
                  <p className="text-sm text-slate-700 dark:text-slate-300 font-medium">{item.label}</p>
                </div>
                <p className="text-lg font-bold text-slate-800 dark:text-slate-100">{item.loading ? <Skeleton className="h-5 w-10 dark:bg-slate-600"/> : item.value}</p>
              </div>
            ))}
          </CardContent>
        </Card>
        
        <Card className="lg:col-span-2 dark:bg-slate-800 dark:border-slate-700 shadow-lg">
          <CardHeader><CardTitle className="text-lg font-semibold dark:text-slate-100 flex items-center"><FiActivity className="mr-2 text-blue-500"/>Recent Activity</CardTitle></CardHeader>
          <CardContent><div className="space-y-2 max-h-72 overflow-y-auto pr-2 custom-scrollbar">
            {isLoading && recentActivities.length === 0 ? ([...Array(3)].map((_, i) => <Skeleton key={i} className="h-12 w-full dark:bg-slate-700 rounded-lg mb-2" />))
             : recentActivities.length === 0 ? (<p className="text-sm text-slate-500 dark:text-slate-400 italic p-3 text-center">No recent activity.</p>)
             : (recentActivities.map((activity) => (
                <div key={activity.id} className="flex items-start space-x-3 p-2.5 bg-slate-50 dark:bg-slate-700/60 rounded-lg">
                  <span className="flex-shrink-0 mt-1 text-slate-500 dark:text-slate-400">{React.isValidElement(activity.icon) ? activity.icon : <FiActivity className="text-gray-500"/>}</span>
                  <div><p className="text-sm text-slate-700 dark:text-slate-300 leading-snug">{activity.text}</p><p className="text-xs text-slate-400 dark:text-slate-500">{activity.timestamp ? new Date(activity.timestamp).toLocaleString() : 'N/A'}</p></div>
                </div>)))}
          </div></CardContent>
        </Card>
      </div>
      
      {/* Chart Sections - Using imported components */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 mt-6 md:mt-8">
          <Card className="dark:bg-slate-800 dark:border-slate-700 shadow-lg">
              <CardHeader><CardTitle className="text-lg font-semibold dark:text-slate-100 flex items-center"><FiBarChart2 className="mr-2 text-indigo-500"/>Conversation Trends</CardTitle></CardHeader>
              <CardContent className="h-80 bg-slate-50 dark:bg-slate-700/50 rounded-md p-4 flex items-center justify-center">
                  { ConversationTrendChart ? <ConversationTrendChart data={conversationTrendsData} isLoading={isLoading} /> : <p className="text-center text-sm text-slate-500 dark:text-slate-400">Chart component not loaded.</p> }
              </CardContent>
          </Card>
           <Card className="dark:bg-slate-800 dark:border-slate-700 shadow-lg">
              <CardHeader><CardTitle className="text-lg font-semibold dark:text-slate-100 flex items-center"><FiCpu className="mr-2 text-rose-500"/>Bot Performance</CardTitle></CardHeader>
              <CardContent className="h-80 bg-slate-50 dark:bg-slate-700/50 rounded-md p-4 flex items-center justify-center">
                  { BotPerformanceDisplay ? <BotPerformanceDisplay data={botPerformanceData} isLoading={isLoading} /> : <p className="text-center text-sm text-slate-500 dark:text-slate-400">Performance display not loaded.</p> }
              </CardContent>
          </Card>
      </div>
    </div>
  );
}