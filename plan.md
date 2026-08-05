# Trendit Bistro Mock Mode Implementation Plan

This document outlines the strategy for bypassing Google Business Profile (GBP) API quota limits while continuing development and testing of the Trendit platform.

## 1. Problem Statement
The Google Cloud project (ID: `612477615512`) currently has a zero-quota for GBP APIs, blocking location discovery and review management for new users.

## 2. Solution: Trendit Bistro Mirror Mode
We are implementing a "Mirror Mode" that provides a fully functional dashboard using mock data for "Trendit Bistro".

### Key Components:
- **Mock Identity**: All non-team users are assigned the location ID `accounts/mock123/locations/loc456`.
- **Team Bypass**: Specific team emails (`eritageentcare@gmail.com`, `trendexhub@gmail.com`) will attempt real discovery first.
- **Quota Fallback**: If real discovery fails (e.g., due to 429 Resource Exhausted error), team members will also be assigned the mock profile to ensure the app stays functional.
- **MCP Server Mocking**: The Model Context Protocol (MCP) server is configured to return realistic "Trendit Bistro" reviews when the `ENABLE_MOCK_MODE` environment variable is set.

## 3. Configuration
- `ENABLE_MOCK_MODE`: Global toggle in `app/config.py`.
- `TEAM_EMAILS`: Authorized emails for real API attempts.

## 4. Transition to Production
Once Google approves the quota increase:
1. Set `ENABLE_MOCK_MODE=false` in Render environment variables.
2. Users can trigger a re-discovery of their actual GBP profiles.

## 5. Verification Steps
- Login with a non-team email: Should see "Trendit Bistro" dashboard.
- Login with a team email: Should attempt real discovery (and fallback to Bistro if quota is still zero).
- AI Reply generation: Should work seamlessly with mock review text.
