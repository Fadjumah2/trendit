/**
 * Google My Business API Client
 * Handles low-level HTTP communication with Google My Business API
 */

import { GoogleAuthService } from './googleAuth.js';
import { logger } from '../utils/logger.js';
import { GOOGLE_API, ERROR_CODES } from '../utils/constants.js';
import { buildApiUrl } from '../utils/pathHelpers.js';

export class GoogleMyBusinessApiClient {
    constructor(private authService: GoogleAuthService) {}
    
    private async accessToken(locationId: string): Promise<string> {
        await this.authService.refreshTokenIfNeeded(locationId);
        const auth = await this.authService.getAuthenticatedClient(locationId);
        return (await auth.getAccessToken()).token!;
    }

    /**
     * Makes an authenticated GET request to the API. Pass `baseUrl` to hit a
     * non-default host (e.g. GOOGLE_API.HOSTS.PERFORMANCE for daily metrics).
     */
    async get<T = any>(locationId: string, path: string, params?: Record<string, any>, baseUrl?: string): Promise<T> {
        const token = await this.accessToken(locationId);
        const url = buildApiUrl(baseUrl ?? GOOGLE_API.BASE_URL, path, params);
        logger.debug(`API GET Request`, { url });
        const fetch = (await import('node-fetch')).default;
        const response = await fetch(url, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        });
        return this.handleResponse<T>(response);
    }

    async put<T = any>(locationId: string, path: string, body: any, baseUrl?: string): Promise<T> {
        const token = await this.accessToken(locationId);
        const url = `${baseUrl ?? GOOGLE_API.BASE_URL}/${path}`;
        logger.debug(`API PUT Request`, { url, body });
        const fetch = (await import('node-fetch')).default;
        const response = await fetch(url, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        return this.handleResponse<T>(response);
    }

    async post<T = any>(locationId: string, path: string, body: any, baseUrl?: string): Promise<T> {
        const token = await this.accessToken(locationId);
        const url = `${baseUrl ?? GOOGLE_API.BASE_URL}/${path}`;
        logger.debug(`API POST Request`, { url });
        const fetch = (await import('node-fetch')).default;
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        return this.handleResponse<T>(response);
    }

    async patch<T = any>(locationId: string, path: string, body: any, params?: Record<string, any>, baseUrl?: string): Promise<T> {
        const token = await this.accessToken(locationId);
        const url = buildApiUrl(baseUrl ?? GOOGLE_API.BASE_URL, path, params);
        logger.debug(`API PATCH Request`, { url, body });
        const fetch = (await import('node-fetch')).default;
        const response = await fetch(url, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        return this.handleResponse<T>(response);
    }

    async delete<T = any>(locationId: string, path: string, baseUrl?: string): Promise<T> {
        const token = await this.accessToken(locationId);
        const url = `${baseUrl ?? GOOGLE_API.BASE_URL}/${path}`;
        logger.debug(`API DELETE Request`, { url });
        const fetch = (await import('node-fetch')).default;
        const response = await fetch(url, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        });
        // DELETE often returns empty body; tolerate that
        if (response.status === 204) return {} as T;
        return this.handleResponse<T>(response);
    }
    
    /**
     * Handles API response and error processing
     */
    private async handleResponse<T>(response: any): Promise<T> {
        if (!response.ok) {
            const errorText = await response.text();
            logger.error(`API request failed: ${response.status}`, { errorText });
            
            throw new Error(`API request failed: ${response.status} - ${errorText}`);
        }
        
        const data = await response.json();
        logger.debug(`API Response received`, { status: response.status });
        
        return data as T;
    }
    
    /**
     * Gets the first account from the authenticated user
     */
    async getFirstAccount(locationId: string): Promise<any> {
        const auth = await this.authService.getAuthenticatedClient(locationId);
        const { google } = await import('googleapis');
        const mybusinessaccountmanagement = google.mybusinessaccountmanagement({ 
            version: 'v1', 
            auth 
        });
        
        const response = await mybusinessaccountmanagement.accounts.list({
            pageSize: 1
        });
        
        const accounts = response.data.accounts || [];
        
        if (accounts.length === 0) {
            throw new Error('No business accounts found');
        }
        
        return accounts[0];
    }
}
