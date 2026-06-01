// ---- API 通用 ----
export interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

// ---- 用户 ----
export interface User {
  user_id: string;
  username: string;
  display_name: string;
  user_role: 'admin' | 'reviewer';
  email: string | null;
  phone: string | null;
  is_active: boolean;
  last_login: string | null;
  created_at: string | null;
}

// ---- 认证 ----
export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  display_name?: string;
  email?: string;
  phone?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse {
  user: User;
  tokens: TokenResponse;
}

export interface RefreshRequest {
  refresh_token: string;
}

// ---- 预测 ----
export interface FieldOption {
  name: string;
  label: string;
  type: 'select' | 'number';
  group: string;
  required: boolean;
  options?: string[];
  min?: number;
  step?: number;
  placeholder?: string;
}

export interface FieldOptionsResponse {
  fields: FieldOption[];
  groups: string[];
}

export interface PredictSingleRequest {
  insuree_id: string;
  ICD10_CHAPTER: string;
  BH_PREFIX: string;
  BH_CATEGORY: string;
  MBR_TYPE: string;
  BEN_TYPE: string;
  KIND_CODE: string;
  POCY_PLAN_DESC: string;
  SUB_AMT: number;
  TOTAL_RECEIPT_AMT: number;
  ORG_PRES_AMT_VALUE: number;
  COPAY_PCT: number;
  NO_OF_YR: number;
  POLICY_CNT: number;
  INVOICE_CNT: number;
  DAYS_INCUR_TO_PAY: number;
  DAYS_RCV_TO_CLOSE: number;
  DAYS_HOSPITALIZATION: number;
  DAYS_RCV_TO_PAY: number;
  IS_INPATIENT: number;
  INCUR_MONTH: number;
  INCUR_DAYOFWEEK: number;
  INCUR_QUARTER: number;
  INCUR_IS_WEEKEND: number;
  PROV_LEVEL_ORDINAL: number;
  RECEIPT_TO_SUB_RATIO: number;
  IS_NEW_INSURED: number;
  IS_LONGTERM_INSURED: number;
}

export interface ShapItem {
  feature: string;
  value: number;
  shap_value: number;
  direction: string;
}

export interface PredictSingleResponse {
  id: number;
  fraud_prob: number;
  raw_prob: number;
  risk_level: 'high' | 'medium' | 'low';
  threshold_used: number;
  feature_values: Record<string, number>;
  shap_top10: ShapItem[];
  detect_time: string;
}
