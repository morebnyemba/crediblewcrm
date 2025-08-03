// src/hooks/useDashboardData.js
import React, { useState, useEffect, useCallback } from 'react';
import { 
  FiLoader, FiCheckCircle, FiAlertCircle, FiMessageCircle, FiUsers, FiTrendingUp, 
  FiHardDrive, FiActivity, FiSettings, FiZap 
} from 'react-icons/fi';
import { apiCall } from '@/lib/api';

const initialStatCardsDefinition = [
  { id: "active_conversations_count", title: "Active Conversations", defaultIcon: <FiMessageCircle />, linkTo: "/conversation", colorScheme: "green", trendKey: null, valueSuffix: "" },
  { id: "new_contacts_today", title: "New Contacts (Today)", defaultIcon: <FiUsers />, linkTo: "/contacts", colorScheme: "emerald", trendKey: "total_contacts", valueSuffix: "" },
  { id: "messages_sent_24h", title: "Messages Sent (24h)", defaultIcon: <FiTrendingUp />, linkTo: null, colorScheme: "lime", trendKey: "messages_sent_automated_percent_text", valueSuffix: "" },
  { id: "meta_configs_total", title: "Meta API Configs", defaultIcon: <FiHardDrive />, linkTo: "/api-settings", colorScheme: "teal", trendKey: "meta_config_active_name", valueSuffix: "" },
  { id: "pending_human_handovers", title: "Pending Handovers", defaultIcon: <FiAlertCircle />, linkTo: "/contacts?filter=needs_intervention", colorScheme: "red", trendKey: "pending_human_handovers_priority_text", valueSuffix: "" },
];

const activityIcons = {
  FiUsers, FiZap, FiMessageCircle, FiSettings, FiCheckCircle, FiAlertCircle,
  default: FiActivity,
};

export function useDashboardData() {
  const [statsCardsData, setStatsCardsData] = useState(initialStatCardsDefinition.map(card => ({...card, value: "...", trend: "..."})));
  const [recentActivities, setRecentActivities] = useState([]);
  const [flowInsights, setFlowInsights] = useState({ activeFlows: "...", completedToday: "...", avgSteps: "..." });
  const [conversationTrendsData, setConversationTrendsData] = useState([]);
  const [botPerformanceData, setBotPerformanceData] = useState({});
  const [systemStatus, setSystemStatus] = useState({ status: "Initializing...", color: "text-yellow-500 dark:text-yellow-400", icon: <FiLoader className="animate-spin" /> });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const [summaryResult, configsResult] = await Promise.allSettled([
        apiCall('/crm-api/stats/summary/'),
        apiCall('/crm-api/meta/api/configs/', { isPaginatedFallback: true }),
      ]);

      const summary = (summaryResult.status === "fulfilled" && summaryResult.value) ? summaryResult.value : {};
      const statsFromSummary = summary.stats_cards || {};
      const insightsFromSummary = summary.flow_insights || {};
      const chartsFromSummary = summary.charts_data || {};
      const activitiesFromApi = summary.recent_activity_log || [];

      let newStats = JSON.parse(JSON.stringify(initialStatCardsDefinition));
      
      if (configsResult.status === "fulfilled" && configsResult.value) {
        const cfData = configsResult.value;
        const configCount = cfData.count ?? 0;
        const activeOne = cfData.results?.find(c => c.is_active);
        const metaConfigStatIdx = newStats.findIndex(s => s.id === "meta_configs_total");
        if(metaConfigStatIdx !== -1) {
            newStats[metaConfigStatIdx].value = configCount.toString();
            newStats[metaConfigStatIdx].trend = activeOne ? `1 Active` : `${configCount} Total`;
        }
      } else if (configsResult.status === "rejected") {
        setError(prev => `${prev} Meta Configs: ${configsResult.reason.message}; `.trimStart());
      }
      
      newStats = newStats.map(card => {
          if (card.id === "meta_configs_total") return card; 
          const summaryValue = statsFromSummary[card.id]?.toString();
          if (summaryValue !== undefined) {
              let trendText = card.trendKey && statsFromSummary[card.trendKey] ? (statsFromSummary[card.trendKey] || "") : (card.trend || "...");
              if (card.id === "messages_sent_24h" && summary.bot_performance_data?.automated_resolution_rate !== undefined) {
                trendText = `${(summary.bot_performance_data.automated_resolution_rate * 100).toFixed(0)}% Auto`;
              }
              return {...card, value: summaryValue || "0", trend: trendText };
          }
          return {...card, value: "N/A", trend: (summaryResult.status === "rejected" ? "Error" : "N/A")};
      });
      setStatsCardsData(newStats);

      setFlowInsights({ activeFlows: insightsFromSummary.active_flows_count || 0, completedToday: insightsFromSummary.flow_completions_today || 0, avgSteps: insightsFromSummary.avg_steps_per_flow?.toFixed(1) || 0 });
      setConversationTrendsData(chartsFromSummary.conversation_trends || []);
      setBotPerformanceData(chartsFromSummary.bot_performance || {});
      setRecentActivities(activitiesFromApi.map(act => ({...act, icon: React.createElement(activityIcons[act.iconName] || activityIcons.default, { className: `${act.iconColor || "text-gray-500"} h-5 w-5` }) })));
      
      if (summaryResult.status === "fulfilled") {
        setSystemStatus({ status: summary.system_status || "Operational", color: "text-green-500 dark:text-green-400", icon: <FiCheckCircle /> });
      } else {
         setSystemStatus({ status: "Data Error", color: "text-orange-500 dark:text-orange-400", icon: <FiAlertCircle /> });
         setError(prev => `${prev} Summary: ${summaryResult.reason.message}; `.trimStart());
      }
    } catch (err) { 
      setError(prev => `${prev} Dashboard fetch failed: {err.message}`.trimStart());
      setSystemStatus({ status: "System Error", color: "text-red-500 dark:text-red-400", icon: <FiAlertCircle /> });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { statsCardsData, recentActivities, flowInsights, conversationTrendsData, botPerformanceData, systemStatus, isLoading, error, refetch: fetchData };
}