/**
 * Insights service — Business Profile Performance API.
 *
 * Daily metrics, monthly search keywords, multi-metric batch reports.
 *
 * GBP API surface: HOSTS.PERFORMANCE (businessprofileperformance.googleapis.com/v1)
 *   GET locations/{l}:fetchMultiDailyMetricsTimeSeries
 *   GET locations/{l}/dailyMetricsTimeSeries:get             (legacy single)
 *   GET locations/{l}/searchkeywords/impressions/monthly
 *
 * Daily metric names (DailyMetric enum):
 *   BUSINESS_IMPRESSIONS_DESKTOP_MAPS, BUSINESS_IMPRESSIONS_DESKTOP_SEARCH,
 *   BUSINESS_IMPRESSIONS_MOBILE_MAPS,  BUSINESS_IMPRESSIONS_MOBILE_SEARCH,
 *   BUSINESS_CONVERSATIONS, BUSINESS_DIRECTION_REQUESTS, CALL_CLICKS,
 *   WEBSITE_CLICKS, BUSINESS_BOOKINGS, BUSINESS_FOOD_ORDERS, BUSINESS_FOOD_MENU_CLICKS
 *
 * STATUS: stubbed.
 */

import { GoogleMyBusinessApiClient } from './apiClient.js';
import { GOOGLE_API } from '../utils/constants.js';
import { logger } from '../utils/logger.js';

export type DailyMetric =
    | 'BUSINESS_IMPRESSIONS_DESKTOP_MAPS' | 'BUSINESS_IMPRESSIONS_DESKTOP_SEARCH'
    | 'BUSINESS_IMPRESSIONS_MOBILE_MAPS'  | 'BUSINESS_IMPRESSIONS_MOBILE_SEARCH'
    | 'BUSINESS_CONVERSATIONS' | 'BUSINESS_DIRECTION_REQUESTS'
    | 'CALL_CLICKS' | 'WEBSITE_CLICKS' | 'BUSINESS_BOOKINGS'
    | 'BUSINESS_FOOD_ORDERS' | 'BUSINESS_FOOD_MENU_CLICKS';

export interface DateRange {
    startDate: { year: number; month: number; day: number };
    endDate:   { year: number; month: number; day: number };
}

function extractLocationId(name?: string): string {
    if (!name) return '';
    const parts = name.split('/');
    const idx = parts.indexOf('locations');
    if (idx !== -1 && idx + 1 < parts.length) {
        return parts[idx + 1];
    }
    return parts[parts.length - 1] || '';
}

export class InsightsService {
    constructor(private apiClient: GoogleMyBusinessApiClient, private mockMode = false) {}

    async dailyMetric(locationName: string, metric: DailyMetric, range: DateRange) {
        if (this.mockMode) return this.mockSeries(metric);
        const locId = extractLocationId(locationName);
        return this.apiClient.get(
            locId,
            `${locationName}/dailyMetricsTimeSeries:get`,
            {
                dailyMetric: metric,
                'dailyRange.startDate.year': range.startDate.year,
                'dailyRange.startDate.month': range.startDate.month,
                'dailyRange.startDate.day': range.startDate.day,
                'dailyRange.endDate.year': range.endDate.year,
                'dailyRange.endDate.month': range.endDate.month,
                'dailyRange.endDate.day': range.endDate.day
            },
            GOOGLE_API.HOSTS.PERFORMANCE
        );
    }

    async multiDailyMetrics(locationName: string, metrics: DailyMetric[], range: DateRange) {
        if (this.mockMode) {
            logger.info('mock insightsService.multiDailyMetrics', { metrics });
            return { multiDailyMetricTimeSeries: metrics.map(m => ({ dailyMetricTimeSeries: this.mockSeries(m) })) };
        }
        const locId = extractLocationId(locationName);
        return this.apiClient.get(
            locId,
            `${locationName}:fetchMultiDailyMetricsTimeSeries`,
            {
                dailyMetrics: metrics.join(','),
                'dailyRange.startDate.year': range.startDate.year,
                'dailyRange.startDate.month': range.startDate.month,
                'dailyRange.startDate.day': range.startDate.day,
                'dailyRange.endDate.year': range.endDate.year,
                'dailyRange.endDate.month': range.endDate.month,
                'dailyRange.endDate.day': range.endDate.day
            },
            GOOGLE_API.HOSTS.PERFORMANCE
        );
    }

    async searchKeywords(locationName: string, monthlyRange: { startMonth: { year: number; month: number }; endMonth: { year: number; month: number } }) {
        if (this.mockMode) {
            return {
                searchKeywordsCounts: [
                    { searchKeyword: 'premature ejaculation doctor charlotte', insightsValue: { value: '40' } },
                    { searchKeyword: 'mens sexual health charlotte nc', insightsValue: { value: '28' } },
                    { searchKeyword: 'pelvic floor therapy charlotte', insightsValue: { value: '15' } }
                ]
            };
        }
        const locId = extractLocationId(locationName);
        return this.apiClient.get(
            locId,
            `${locationName}/searchkeywords/impressions/monthly`,
            {
                'monthlyRange.startMonth.year': monthlyRange.startMonth.year,
                'monthlyRange.startMonth.month': monthlyRange.startMonth.month,
                'monthlyRange.endMonth.year': monthlyRange.endMonth.year,
                'monthlyRange.endMonth.month': monthlyRange.endMonth.month
            },
            GOOGLE_API.HOSTS.PERFORMANCE
        );
    }

    private mockSeries(metric: DailyMetric) {
        const today = new Date();
        const points = Array.from({ length: 7 }, (_, i) => {
            const d = new Date(today);
            d.setDate(d.getDate() - (6 - i));
            return {
                date: { year: d.getFullYear(), month: d.getMonth() + 1, day: d.getDate() },
                value: String(Math.floor(Math.random() * 50 + 10))
            };
        });
        return { dailyMetric: metric, timeSeries: { datedValues: points } };
    }
}
