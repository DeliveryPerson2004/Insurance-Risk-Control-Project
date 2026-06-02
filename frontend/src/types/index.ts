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
  feature_values: Record<string, number | string>;
  shap_top10: ShapItem[];
  detect_time: string;
}

// ---- 仪表盘 ----
export interface DashboardStats {
  today_pending: number;
  today_high_risk: number;
  today_processed: number;
  total_detected: number;
}

export interface TrendItem {
  date: string;
  total: number;
  fraud_rate: number;
}

export interface HighRiskItem {
  id: number;
  policy_id: string;
  fraud_prob: number;
  risk_level: string;
  claim_amount: number | null;
  detect_time: string;
}

// ---- 批量预测 ----
export interface BatchTaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total: number;
  processed: number;
  success: number;
  failed: number;
  result_filename: string | null;
  error_message: string | null;
}

export interface BatchTaskItem {
  task_id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total: number | null;
  processed: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface BatchTaskListResponse {
  items: BatchTaskItem[];
  total: number;
  page: number;
  size: number;
}

// ---- 案件管理 ----
export interface CaseListItem {
  id: number;
  policy_id: string;
  fraud_prob: number;
  raw_prob: number | null;
  risk_level: string;
  claim_amount: number | null;
  manual_result: string | null;
  detect_time: string;
  has_agent_report: boolean;
}

export interface CaseListResponse {
  items: CaseListItem[];
  total: number;
  page: number;
  size: number;
}

export interface CaseDetailInsuree {
  insuree_id: string;
  age: number | null;
  gender: string | null;
  occupation: string | null;
}

export interface CaseDetailPolicy {
  policy_id: string;
  insurance_type: string | null;
  insurance_amount: number | null;
  premium: number | null;
}

export interface CaseDetailClaim {
  id: number;
  accident_date: string | null;
  accident_type: string | null;
  claim_amount: number | null;
  claim_date: string | null;
  is_fraud: boolean | null;
  is_paid: boolean | null;
}

export interface CaseHistoryItem {
  id: number;
  manual_result: string | null;
  remark: string | null;
  operate_time: string;
  reviewer_name: string | null;
}

export interface CaseDetailResponse {
  id: number;
  policy_id: string;
  fraud_prob: number;
  raw_prob: number | null;
  risk_level: string;
  threshold_used: number | null;
  feature_values: Record<string, unknown> | null;
  shap_values: Record<string, number> | null;
  agent_report: { report_text: string; model_used: string; generated_at: string } | null;
  manual_result: string | null;
  detect_time: string;
  insuree: CaseDetailInsuree | null;
  policy: CaseDetailPolicy | null;
  accident_claim: CaseDetailClaim | null;
  case_history: CaseHistoryItem[];
}

export interface AdjudicateRequest {
  manual_result: 'pass' | 'reject' | 'investigate';
  remark?: string;
}

export interface CaseStatsSummary {
  total: number;
  by_risk_level: Record<string, number>;
  by_manual_result: Record<string, number>;
}
