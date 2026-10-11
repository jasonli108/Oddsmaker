/**
 * Friendly names for the API shapes. The shapes themselves are generated from the backend's
 * pydantic models into schema.d.ts: run `make types` after backend/app/schemas.py changes.
 * Never edit schema.d.ts by hand.
 */
import type { components } from './schema';

type S = components['schemas'];

export type Team = S['Team'];
export type TeamCreate = S['TeamCreate'];
export type User = S['User'];
export type LeaderboardEntry = S['LeaderboardEntry'];
export type MarketSummary = S['MarketSummary'];
export type MarketDetail = S['MarketDetail'];
export type MarketTeam = S['MarketTeam'];
export type MarketHistory = S['MarketHistory'];
export type TeamSeries = S['TeamSeries'];
export type BetFeedItem = S['BetFeedItem'];
export type ScoutFeedItem = S['ScoutFeedItem'];
export type FeedItem = BetFeedItem | ScoutFeedItem;
export type BetCreate = S['BetCreate'];
export type BetReceipt = S['BetReceipt'];
export type ScoutReport = S['ScoutReport'];
export type TeamReport = S['TeamReport'];
export type ResolveResult = S['ResolveResult'];
