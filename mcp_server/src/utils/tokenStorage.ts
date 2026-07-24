/**
 * Token storage utilities — multi-tenant, Postgres-backed.
 *
 * REPLACES the original single-file implementation (.tokens.json).
 * All reads and writes now go through the Python FastAPI backend's
 * internal endpoint, which owns encryption and the gbp_credentials table.
 *
 * Required env vars (same ones already set in Render):
 *   BACKEND_URL      — base URL of the Python backend, e.g. https://your-app.onrender.com
 *   INTERNAL_TOKEN   — shared secret sent as X-Internal-Token header
 *
 * Only `locationId` is used as the key — Google location IDs are globally
 * unique, so `customerId` is not needed for routing.  The backend's own
 * gbp_credentials table still stores customer_id for billing/auditing; we
 * just don't need to pass it from here.
 */

import { getConfig } from './config.js';
import { logger } from './logger.js';
import type { GoogleOAuthTokens } from '../types/index.js';

function getBackendHeaders() {
    const { internalToken } = getConfig();
    if (!internalToken) {
        logger.warn('⚠️  INTERNAL_TOKEN is not set — /internal/gbp-credentials calls will be rejected by the backend.');
    }
    return { 'X-Internal-Token': internalToken ?? '' };
}

function backendUrl(): string {
    return getConfig().backendUrl ?? 'http://localhost:8080';
}

/** Shape returned by GET /internal/gbp-credentials */
interface BackendCredentials {
    access_token: string;
    refresh_token: string;
    token_expires_at: string; // ISO-8601 datetime string
    account_id: string | null;
    scopes: string | null;
}

/**
 * Fetch tokens for a specific location from the Python backend.
 * Returns null if no credentials exist yet (customer hasn't connected GBP).
 *
 * Token shape uses `expiry_date` (milliseconds epoch) to match the
 * field that googleapis' OAuth2Client reads/writes natively.
 */
export async function loadTokensForLocation(
    locationId: string,
): Promise<GoogleOAuthTokens | null> {
    try {
        const url = new URL('/internal/gbp-credentials', backendUrl());
        url.searchParams.set('location_id', locationId);

        const res = await fetch(url.toString(), {
            headers: getBackendHeaders(),
        });

        if (res.status === 404) {
            logger.debug(`No credentials found for location=${locationId}`);
            return null;
        }

        if (!res.ok) {
            logger.error(`Backend credential fetch failed: ${res.status} ${res.statusText}`);
            return null;
        }

        const data: BackendCredentials = await res.json();
        const expiryDate = new Date(data.token_expires_at).getTime();

        logger.debug(`Loaded tokens for location=${locationId}`);
        return {
            access_token: data.access_token,
            refresh_token: data.refresh_token,
            scope: data.scopes ?? '',
            token_type: 'Bearer',
            // expiry_date is what googleapis OAuth2Client expects natively
            expiry_date: expiryDate,
        };
    } catch (error) {
        logger.error('Error loading tokens from backend:', error);
        return null;
    }
}

/**
 * Persist a refreshed token set back to the Python backend.
 * Called after a successful token refresh so the new access_token lands
 * in Postgres rather than being discarded.
 *
 * NOTE: the *initial* token save after an OAuth callback is done directly
 * by the website's OAuth callback handler (Python) — this function only
 * handles *subsequent* refreshes originating inside this Node process.
 */
export async function saveRefreshedTokensForLocation(
    locationId: string,
    tokens: GoogleOAuthTokens,
): Promise<boolean> {
    try {
        const url = new URL('/internal/gbp-credentials', backendUrl());

        // expiry_date (ms epoch) → ISO-8601 for the backend
        const expiresAt = tokens.expiry_date
            ? new Date(tokens.expiry_date).toISOString()
            : new Date(Date.now() + 3_600_000).toISOString();

        const res = await fetch(url.toString(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getBackendHeaders(),
            },
            body: JSON.stringify({
                location_id: locationId,
                access_token: tokens.access_token,
                refresh_token: tokens.refresh_token,
                token_expires_at: expiresAt,
                scopes: tokens.scope ?? null,
            }),
        });

        if (!res.ok) {
            logger.error(`Backend credential save failed: ${res.status} ${res.statusText}`);
            return false;
        }

        logger.debug(`Saved refreshed tokens for location=${locationId}`);
        return true;
    } catch (error) {
        logger.error('Error saving tokens to backend:', error);
        return false;
    }
}

/**
 * Check whether credentials exist for a location.
 */
export async function hasStoredTokens(locationId: string): Promise<boolean> {
    const tokens = await loadTokensForLocation(locationId);
    return tokens !== null;
}

/**
 * Clear credentials for a location (e.g. on disconnect).
 * Delegates to the backend's DELETE endpoint.
 */
export async function clearTokens(locationId: string): Promise<boolean> {
    try {
        const url = new URL('/internal/gbp-credentials', backendUrl());
        url.searchParams.set('location_id', locationId);

        const res = await fetch(url.toString(), {
            method: 'DELETE',
            headers: getBackendHeaders(),
        });

        if (!res.ok && res.status !== 404) {
            logger.error(`Backend credential clear failed: ${res.status} ${res.statusText}`);
            return false;
        }

        logger.debug(`Cleared tokens for location=${locationId}`);
        return true;
    } catch (error) {
        logger.error('Error clearing tokens from backend:', error);
        return false;
    }
}
