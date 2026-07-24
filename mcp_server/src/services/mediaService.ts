/**
 * Media service — photos and videos on a Google Business Profile location.
 *
 * GBP API surface: legacy v4
 *   GET    accounts/{a}/locations/{l}/media                → list
 *   POST   accounts/{a}/locations/{l}/media                → create from sourceUrl
 *   POST   accounts/{a}/locations/{l}/media:startUpload    → begin byte upload (returns resourceName)
 *   DELETE accounts/{a}/locations/{l}/media/{m}            → delete
 *
 * STATUS: stubbed.
 */

import { GoogleMyBusinessApiClient } from './apiClient.js';
import { logger } from '../utils/logger.js';

export type MediaCategory =
    | 'COVER' | 'PROFILE' | 'LOGO' | 'EXTERIOR' | 'INTERIOR'
    | 'PRODUCT' | 'AT_WORK' | 'FOOD_AND_DRINK' | 'MENU' | 'COMMON_AREA'
    | 'ROOMS' | 'TEAMS' | 'ADDITIONAL';

export interface MediaItem {
    name?: string;
    mediaFormat: 'PHOTO' | 'VIDEO';
    locationAssociation?: { category?: MediaCategory; priceListItemId?: string };
    googleUrl?: string;
    thumbnailUrl?: string;
    createTime?: string;
    sourceUrl?: string;
    dataRef?: { resourceName: string };
    description?: string;
    attribution?: any;
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

export class MediaService {
    constructor(private apiClient: GoogleMyBusinessApiClient, private mockMode = false) {}

    async list(locationName: string, pageSize = 100, pageToken?: string) {
        if (this.mockMode) return { mediaItems: [], totalMediaItemCount: 0, nextPageToken: undefined };
        const locId = extractLocationId(locationName);
        return this.apiClient.get<{ mediaItems: MediaItem[]; totalMediaItemCount: number; nextPageToken?: string }>(
            locId,
            `${locationName}/media`,
            { pageSize, pageToken }
        );
    }

    async createFromUrl(locationName: string, sourceUrl: string, category: MediaCategory, format: 'PHOTO' | 'VIDEO' = 'PHOTO', description?: string) {
        if (this.mockMode) {
            logger.info('mock mediaService.createFromUrl', { locationName, sourceUrl, category });
            return { name: `${locationName}/media/mock-${Date.now()}`, mediaFormat: format, sourceUrl, locationAssociation: { category } } as MediaItem;
        }
        const locId = extractLocationId(locationName);
        return this.apiClient.post<MediaItem>(locId, `${locationName}/media`, {
            mediaFormat: format,
            sourceUrl,
            locationAssociation: { category },
            description
        });
    }

    async startUpload(locationName: string) {
        if (this.mockMode) return { resourceName: `${locationName}/media/mock-upload-${Date.now()}` };
        const locId = extractLocationId(locationName);
        return this.apiClient.post<{ resourceName: string }>(locId, `${locationName}/media:startUpload`, {});
    }

    async delete(mediaName: string) {
        if (this.mockMode) { logger.info('mock mediaService.delete', { mediaName }); return { ok: true }; }
        const locId = extractLocationId(mediaName);
        await this.apiClient.delete(locId, mediaName);
        return { ok: true };
    }
}
