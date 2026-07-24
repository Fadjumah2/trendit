/**
 * Local Posts service — Google Business Profile updates, offers, events, CTAs.
 *
 * GBP API surface: legacy v4 host (mybusiness.googleapis.com/v4)
 *   GET    accounts/{a}/locations/{l}/localPosts          → list
 *   GET    accounts/{a}/locations/{l}/localPosts/{p}      → get
 *   POST   accounts/{a}/locations/{l}/localPosts          → create
 *   PATCH  accounts/{a}/locations/{l}/localPosts/{p}      → update (with updateMask)
 *   DELETE accounts/{a}/locations/{l}/localPosts/{p}      → delete
 *
 * STATUS: stubbed. Wire real calls when Google Business Profile API access
 * is approved (60+ day waiting list). Mock responses below let the rest of
 * the stack be developed and tested against the tool surface today.
 */

import { GoogleMyBusinessApiClient } from './apiClient.js';
import { logger } from '../utils/logger.js';

export type LocalPostType = 'STANDARD' | 'EVENT' | 'OFFER' | 'ALERT';

export interface LocalPost {
    name?: string;
    languageCode?: string;
    summary: string;
    callToAction?: { actionType: string; url?: string };
    media?: Array<{ mediaFormat: 'PHOTO' | 'VIDEO'; sourceUrl: string }>;
    topicType: LocalPostType;
    event?: { title: string; schedule: { startDate: any; endDate: any } };
    offer?: { couponCode?: string; redeemOnlineUrl?: string; termsConditions?: string };
    state?: 'LIVE' | 'REJECTED' | 'PROCESSING';
    createTime?: string;
    updateTime?: string;
    searchUrl?: string;
}

export class PostService {
    constructor(private apiClient: GoogleMyBusinessApiClient, private mockMode = false) {}

    async list(locationId: string, locationName: string, pageSize = 100, pageToken?: string) {
        if (this.mockMode) {
            return { localPosts: this.mockPosts(), nextPageToken: undefined };
        }
        return this.apiClient.get<{ localPosts: LocalPost[]; nextPageToken?: string }>(
            locationId,
            `${locationName}/localPosts`,
            { pageSize, pageToken }
        );
    }

    async create(locationId: string, locationName: string, post: Partial<LocalPost>) {
        if (this.mockMode) {
            logger.info('mock postService.create', { locationId, locationName, summary: post.summary });
            return { ...post, name: `${locationName}/localPosts/mock-${Date.now()}`, state: 'LIVE', createTime: new Date().toISOString() } as LocalPost;
        }
        return this.apiClient.post<LocalPost>(locationId, `${locationName}/localPosts`, post);
    }

    async update(locationId: string, postName: string, post: Partial<LocalPost>, updateMask: string) {
        if (this.mockMode) {
            logger.info('mock postService.update', { locationId, postName, updateMask });
            return { ...post, name: postName, updateTime: new Date().toISOString() } as LocalPost;
        }
        return this.apiClient.patch<LocalPost>(locationId, postName, post, { updateMask });
    }

    async delete(locationId: string, postName: string) {
        if (this.mockMode) {
            logger.info('mock postService.delete', { locationId, postName });
            return { ok: true };
        }
        await this.apiClient.delete(locationId, postName);
        return { ok: true };
    }

    private mockPosts(): LocalPost[] {
        return [
            {
                name: 'accounts/123/locations/456/localPosts/mock-1',
                summary: 'New patient appointments available next week. Book online or call.',
                topicType: 'STANDARD',
                state: 'LIVE',
                createTime: new Date(Date.now() - 86400000).toISOString(),
                updateTime: new Date(Date.now() - 86400000).toISOString()
            }
        ];
    }
}
