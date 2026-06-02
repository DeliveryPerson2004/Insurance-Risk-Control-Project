import client from './client';
import type {
  ApiResponse,
  CaseListResponse,
  CaseDetailResponse,
  CaseStatsSummary,
  AdjudicateRequest,
} from '../types';

export async function fetchCases(params: {
  page?: number;
  size?: number;
  risk_level?: string;
  manual_result?: string;
  date_from?: string;
  date_to?: string;
  keyword?: string;
}): Promise<CaseListResponse> {
  const res = await client.get<ApiResponse<CaseListResponse>>('/cases', { params });
  return res.data.data;
}

export async function fetchCaseDetail(id: number): Promise<CaseDetailResponse> {
  const res = await client.get<ApiResponse<CaseDetailResponse>>(`/cases/${id}`);
  return res.data.data;
}

export async function adjudicateCase(
  id: number,
  data: AdjudicateRequest,
): Promise<{ id: number; manual_result: string; operate_time: string }> {
  const res = await client.put<
    ApiResponse<{ id: number; manual_result: string; operate_time: string }>
  >(`/cases/${id}/adjudicate`, data);
  return res.data.data;
}

export async function fetchCaseStats(): Promise<CaseStatsSummary> {
  const res = await client.get<ApiResponse<CaseStatsSummary>>('/cases/stats/summary');
  return res.data.data;
}
