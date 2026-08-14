export interface User {
  id: number;
  login: string;
}

export interface Question {
  id: number;
  lp?: number;
  scope: 'PODSTAWOWY' | 'SPECJALISTYCZNY';
  points: number;
  type: 'TN' | 'ABC';
  correct: string;
  media?: string | null;
  media_kind?: string | null;
  categories?: string[];
  q_pl: string;
  a_pl?: string | null;
  b_pl?: string | null;
  c_pl?: string | null;
  axis_a?: string | null;
  axis_b?: string | null;
}

export interface AnswerResponse {
  event_id: number;
  question_id: number;
  chosen: string;
  is_correct: number;
  correct_answer: string;
  explanation?: string | null;
  legal_basis?: string | null;
  pending_explanation: boolean;
  skill_theta_before?: number;
  skill_theta_after?: number;
  delta_theta?: number;
  attempts?: number;
  wrong?: number;
  p_err?: number;
  b_q?: number;
}

export interface DashboardData {
  user: {
    id: number;
    login: string;
    skill_theta: number;
    n: number;
  };
  skill_theta: number;
  per_axis_b: Record<string, number>;
  metrics: {
    total_answers: number;
    correct_answers: number;
    accuracy_percent: number;
    mastered_count: number;
    avg_time_ms: number;
  };
  coverage: {
    total_cat_b: number;
    never_seen: number;
    seen: number;
    mastered: number;
  };
  domain_performance: Array<{
    axis_b: string;
    theta: number;
    error_count: number;
    total_attempts: number;
    accuracy_pct: number;
  }>;
  repeats_due: number;
  reason_split: {
    slips: number;
    mistakes: number;
    uncertainty: number;
  };
  skill_history: Array<{
    id: number;
    theta: number;
    created_at: string;
  }>;
  hardest_questions: Array<{
    id: number;
    q_pl: string;
    scope: string;
    attempts: number;
    wrong: number;
    error_pct: number;
    b_q: number;
  }>;
  recent_activity: Array<{
    id: number;
    question_id: number;
    q_pl: string;
    chosen: string;
    is_correct: number;
    time_ms: number;
    created_at: string;
  }>;
}

export interface AnalyticsCoverage {
  total_cat_b: number;
  mastered: number;
  seen: number;
  never_seen: number;
}

export interface AnalyticsReason {
  slips: number;
  mistakes: number;
  uncertainty: number;
}

export interface AnalyticsHesitation {
  question_id: number;
  q_pl: string;
  time_ms: number;
  chosen: string;
}

export interface AnalyticsAxisItem {
  axis_value: string;
  error_count: number;
}

export interface AnalyticsOptionItem {
  question_id: number;
  chosen: string;
  correct_option: string;
  confused_count: number;
}

export interface AnalyticsHardestItem {
  question_id: number;
  q_pl: string;
  error_count: number;
}

export interface ReviewItem {
  id: number;
  q_pl: string;
  type: string;
  scope: string;
  media?: string | null;
  media_kind?: string | null;
  sugg_a?: string | null;
  conf_a?: number | null;
  sugg_b?: string | null;
  conf_b?: number | null;
}

export interface ExamStartResponse {
  questions: Question[];
  total_questions: number;
  max_score: number;
  pass_threshold: number;
}

export interface ExamSubmissionDetail {
  question_id: number;
  chosen: string;
  correct: string;
  is_correct: boolean;
  points_earned: number;
  time_ms: number;
}

export interface ExamSubmissionResponse {
  exam_id: number;
  score: number;
  max_score: number;
  passed: boolean;
  correct_count: number;
  total_questions: number;
  time_seconds: number;
  details: ExamSubmissionDetail[];
}
