/**
 * Google OAuth Authentication Service — REWRITTEN for multi-tenant use.
 *
 * The original bug: the constructor loaded ONE token set at startup into
 * instance fields (this.tokens, this.oauth2Client with credentials baked
 * in), shared by every caller regardless of which business they belonged
 * to. Any customer's request could see/overwrite another's tokens.
 *
 * Fix: no tokens are loaded or cached at construction time. Every method
 * that needs credentials takes a `locationId` and builds a fresh,
 * unshared OAuth2Client for that one call, fetching/saving tokens via
 * tokenStorage.ts (which talks to the Python backend, not a local file).
 *
 * getAuthUrl/handleCallback are kept only for local dev/testing against
 * your own account — production token issuance happens through the
 * website's OAuth callback, which writes directly to gbp_credentials via
 * the Python backend. Do not wire these into any customer-facing flow.
 */
import { google } from 'googleapis';
import { getConfig } from '../utils/config.js';
import { logger } from '../utils/logger.js';
import { GOOGLE_API } from '../utils/constants.js';
import {
  loadTokensForLocation,
  saveRefreshedTokensForLocation,
} from '../utils/tokenStorage.js';
import type { GoogleOAuthTokens, AuthState } from '../types/index.js';

export class GoogleAuthService {
  private config = getConfig();

  /** Fresh client per call — never cache credentials on `this`. */
  private createOAuth2Client(): any {
    return new google.auth.OAuth2(
      this.config.googleClientId,
      this.config.googleClientSecret,
      this.config.googleRedirectUri,
    );
  }

  /**
   * DEV/TEST ONLY. Production OAuth issuance happens via the website's
   * callback (Python side), not through this server.
   */
  getAuthUrl(state?: string): string {
    const client = this.createOAuth2Client();
    return client.generateAuthUrl({
      access_type: 'offline',
      scope: GOOGLE_API.SCOPES,
      state,
      prompt: 'consent',
    });
  }

  /**
   * DEV/TEST ONLY — see class doc comment.
   */
  async handleCallback(code: string): Promise<GoogleOAuthTokens> {
    const client = this.createOAuth2Client();
    const { tokens } = await client.getToken(code);
    return tokens as GoogleOAuthTokens;
  }

  /**
   * Returns an authenticated googleapis client for ONE specific location,
   * built fresh from that location's own stored tokens. This is what every
   * Local Posts tool (get_local_posts, create_local_post, etc.) should call
   * before making a GBP API request.
   */
  async getAuthenticatedClient(locationId: string): Promise<any> {
    const tokens = await loadTokensForLocation(locationId);
    if (!tokens) {
      throw new Error(
        `No stored credentials for location ${locationId} — has this business connected their GBP profile yet?`,
      );
    }

    const client = this.createOAuth2Client();
    client.setCredentials({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      expiry_date: tokens.expiry_date,
    });

    // googleapis fires this when it auto-refreshes an access token behind
    // the scenes during an API call. Push the new token straight back to
    // Postgres for THIS location — no shared instance state involved.
    client.on('tokens', async (refreshed: GoogleOAuthTokens) => {
      try {
        const merged: GoogleOAuthTokens = {
          ...tokens,
          ...refreshed,
          // Google sometimes omits refresh_token on refresh responses —
          // keep the original one if a new one wasn't issued.
          refresh_token: refreshed.refresh_token ?? tokens.refresh_token,
        };
        await saveRefreshedTokensForLocation(locationId, merged);
      } catch (err) {
        logger.error(`Failed to persist refreshed tokens for ${locationId}: ${err}`);
      }
    });

    return client;
  }

  /**
   * Explicit pre-emptive refresh check, for tools that want to guarantee
   * a valid token before a batch of calls rather than relying on the
   * 'tokens' event firing mid-call.
   */
  async refreshTokenIfNeeded(locationId: string): Promise<void> {
    const tokens = await loadTokensForLocation(locationId);
    if (!tokens) {
      throw new Error(`No stored credentials for location ${locationId}`);
    }

    const isExpired = !tokens.expiry_date || Date.now() >= tokens.expiry_date - 60_000;
    if (!isExpired) {
      return;
    }

    const client = this.createOAuth2Client();
    client.setCredentials({ refresh_token: tokens.refresh_token });
    const { credentials } = await client.refreshAccessToken();

    await saveRefreshedTokensForLocation(locationId, {
      ...tokens,
      ...credentials,
      refresh_token: credentials.refresh_token ?? tokens.refresh_token,
    } as GoogleOAuthTokens);
  }

  /**
   * Per-location auth state check (replaces the old single-tenant
   * getAuthState()). Returns whether a location currently has usable
   * credentials, without exposing the tokens themselves.
   */
  async getAuthState(locationId: string): Promise<AuthState> {
    const tokens = await loadTokensForLocation(locationId);
    if (!tokens) {
      return { authenticated: false } as AuthState;
    }
    const isExpired = !tokens.expiry_date || Date.now() >= tokens.expiry_date;
    return { authenticated: true, expired: isExpired } as AuthState;
  }
}