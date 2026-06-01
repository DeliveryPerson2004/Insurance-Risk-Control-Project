import client from './client';
import type { ApiResponse, FieldOptionsResponse, PredictSingleRequest, PredictSingleResponse } from '../types';

export async function getFieldOptions(): Promise<FieldOptionsResponse> {
  const res = await client.get<ApiResponse<FieldOptionsResponse>>('/predict/field-options');
  return res.data.data;
}

export async function postSinglePredict(data: PredictSingleRequest): Promise<PredictSingleResponse> {
  const res = await client.post<ApiResponse<PredictSingleResponse>>('/predict/single', data);
  return res.data.data;
}
