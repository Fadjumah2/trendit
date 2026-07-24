/**
 * Q&A service — Google Business Profile questions and answers.
 *
 * Critical lever: own your common questions before competitors plant them.
 *
 * GBP API surface: HOSTS.QANDA (mybusinessqanda.googleapis.com/v1)
 *   GET    locations/{l}/questions                                  → list questions
 *   POST   locations/{l}/questions                                  → ask a question (rare for owner)
 *   PATCH  locations/{l}/questions/{q}                              → update own question
 *   DELETE locations/{l}/questions/{q}                              → delete own question
 *   GET    locations/{l}/questions/{q}/answers                      → list answers
 *   PUT    locations/{l}/questions/{q}/answers:upsert               → owner answer
 *   DELETE locations/{l}/questions/{q}/answers/{a}                  → delete answer
 *
 * STATUS: stubbed. Wire when API approval lands.
 */

import { GoogleMyBusinessApiClient } from './apiClient.js';
import { GOOGLE_API } from '../utils/constants.js';
import { logger } from '../utils/logger.js';

export interface Question {
    name?: string;
    author?: { displayName: string; profilePhotoUri?: string; type: string };
    upvoteCount?: number;
    text: string;
    createTime?: string;
    updateTime?: string;
    topAnswers?: Answer[];
    totalAnswerCount?: number;
}

export interface Answer {
    name?: string;
    author?: { displayName: string; profilePhotoUri?: string; type: string };
    upvoteCount?: number;
    text: string;
    createTime?: string;
    updateTime?: string;
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

export class QAService {
    constructor(private apiClient: GoogleMyBusinessApiClient, private mockMode = false) {}

    async listQuestions(locationName: string, pageSize = 50, pageToken?: string, answersPerQuestion = 10) {
        if (this.mockMode) return { questions: this.mockQuestions(), totalSize: 1, nextPageToken: undefined };
        const locId = extractLocationId(locationName);
        return this.apiClient.get<{ questions: Question[]; totalSize: number; nextPageToken?: string }>(
            locId,
            `${locationName}/questions`,
            { pageSize, pageToken, answersPerQuestion },
            GOOGLE_API.HOSTS.QANDA
        );
    }

    async listAnswers(questionName: string, pageSize = 10, pageToken?: string) {
        if (this.mockMode) return { answers: [], totalSize: 0, nextPageToken: undefined };
        const locId = extractLocationId(questionName);
        return this.apiClient.get<{ answers: Answer[]; totalSize: number; nextPageToken?: string }>(
            locId,
            `${questionName}/answers`,
            { pageSize, pageToken },
            GOOGLE_API.HOSTS.QANDA
        );
    }

    async upsertAnswer(questionName: string, text: string) {
        if (this.mockMode) {
            logger.info('mock qaService.upsertAnswer', { questionName, text });
            return { name: `${questionName}/answers/owner`, text, createTime: new Date().toISOString() } as Answer;
        }
        const locId = extractLocationId(questionName);
        return this.apiClient.put<Answer>(locId, `${questionName}/answers:upsert`, { answer: { text } }, GOOGLE_API.HOSTS.QANDA);
    }

    async deleteAnswer(answerName: string) {
        if (this.mockMode) { logger.info('mock qaService.deleteAnswer', { answerName }); return { ok: true }; }
        const locId = extractLocationId(answerName);
        await this.apiClient.delete(locId, answerName, GOOGLE_API.HOSTS.QANDA);
        return { ok: true };
    }

    async deleteQuestion(questionName: string) {
        if (this.mockMode) { logger.info('mock qaService.deleteQuestion', { questionName }); return { ok: true }; }
        const locId = extractLocationId(questionName);
        await this.apiClient.delete(locId, questionName, GOOGLE_API.HOSTS.QANDA);
        return { ok: true };
    }

    private mockQuestions(): Question[] {
        return [
            {
                name: 'locations/456/questions/mock-1',
                text: 'Do you accept new patients for premature ejaculation treatment?',
                author: { displayName: 'Anonymous', type: 'REGULAR_USER' },
                upvoteCount: 3,
                createTime: new Date(Date.now() - 7 * 86400000).toISOString(),
                totalAnswerCount: 0
            }
        ];
    }
}
