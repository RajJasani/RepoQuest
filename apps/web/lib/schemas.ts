import { z } from 'zod';

// ==========================================
// 1. Health & System
// ==========================================
export const HealthResponseSchema = z.object({
  status: z.enum(['ok', 'degraded']).default('ok'),
  db: z.string().optional(),
  database: z.string().optional(),
  ollama: z.string().optional(),
  embedding_dimension_ok: z.boolean().nullable().optional(),
  embedding_dimension_warning: z.string().nullable().optional(),
  version: z.string().default('1.0.0'),
});
export type HealthResponse = z.infer<typeof HealthResponseSchema>;

export const ModelItemSchema = z.object({
  name: z.string(),
  size: z.number().optional(),
  modified_at: z.string().optional(),
  digest: z.string().optional(),
  family: z.string().optional(),
  parameter_size: z.string().optional(),
  quantization_level: z.string().optional(),
});
export type ModelItem = z.infer<typeof ModelItemSchema>;

export const ModelsResponseSchema = z.object({
  models: z.array(ModelItemSchema).default([]),
});
export type ModelsResponse = z.infer<typeof ModelsResponseSchema>;

// ==========================================
// 2. Settings
// ==========================================
export const SettingsResponseSchema = z.object({
  ollama_base_url: z.string(),
  chat_model: z.string(),
  embed_model: z.string(),
  triage_mode: z.enum(['manual', 'assisted', 'auto']).default('assisted'),
  spam_threshold: z.number().default(70),
  language: z.enum(['en', 'hi', 'kn', 'ta']).default('en'),
  offline_mode: z.boolean().default(true),
  has_github_token: z.boolean().default(false),
  updated_at: z.string().optional(),
});
export type SettingsResponse = z.infer<typeof SettingsResponseSchema>;

// ==========================================
// 3. Repositories
// ==========================================
export const RepoSummarySchema = z.object({
  id: z.string(),
  owner: z.string(),
  name: z.string(),
  full_name: z.string(),
  default_branch: z.string().default('main'),
  description: z.string().nullable().optional(),
  stars: z.number().default(0),
  status: z.string(),
  progress: z.number().default(0),
  error: z.string().nullable().optional(),
  last_indexed_at: z.string().nullable().optional(),
  created_at: z.string(),
});
export type RepoSummary = z.infer<typeof RepoSummarySchema>;

export const RepoDetailSchema = RepoSummarySchema.extend({
  languages: z.record(z.string(), z.any()).default({}),
  tech_stack: z.array(z.string()).default([]),
  contributing_md: z.string().nullable().optional(),
  readme_excerpt: z.string().nullable().optional(),
  run_instructions: z.string().nullable().optional(),
  file_count: z.number().default(0),
  labels: z.array(z.any()).default([]),
});
export type RepoDetail = z.infer<typeof RepoDetailSchema>;

export const ReposListResponseSchema = z.array(RepoSummarySchema);
export type ReposListResponse = z.infer<typeof ReposListResponseSchema>;

// ==========================================
// 4. File Tree
// ==========================================
export interface TreeNode {
  name: string;
  path: string;
  type: string;
  size_bytes?: number | null;
  language?: string | null;
  children?: TreeNode[] | null;
}

export const TreeNodeSchema: z.ZodType<TreeNode> = z.lazy(() =>
  z.object({
    name: z.string(),
    path: z.string(),
    type: z.string(),
    size_bytes: z.number().nullable().optional(),
    language: z.string().nullable().optional(),
    children: z.array(TreeNodeSchema).nullable().optional(),
  })
);

export const TreeNodesListSchema = z.array(TreeNodeSchema);
export type TreeNodesList = z.infer<typeof TreeNodesListSchema>;

export const FileTreeResponseSchema = z.union([
  z.object({
    tree: z.array(TreeNodeSchema).default([]),
  }),
  z.array(TreeNodeSchema),
]);
export type FileTreeResponse = z.infer<typeof FileTreeResponseSchema>;

// ==========================================
// 5. Architecture & Explorer
// ==========================================
export const ArchitectureNodeSchema = z.object({
  id: z.string(),
  name: z.string(),
  path: z.string(),
  summary: z.string().nullable().optional(),
  key_files: z.array(z.string()).default([]),
  entry_points: z.array(z.string()).default([]),
  file_count: z.number().default(0),
});
export type ArchitectureNode = z.infer<typeof ArchitectureNodeSchema>;

export const ArchitectureEdgeSchema = z.object({
  source: z.string(),
  target: z.string(),
  weight: z.number().default(1),
});
export type ArchitectureEdge = z.infer<typeof ArchitectureEdgeSchema>;

export const ArchitectureResponseSchema = z.object({
  nodes: z.array(ArchitectureNodeSchema).default([]),
  edges: z.array(ArchitectureEdgeSchema).default([]),
  tech_stack: z.array(z.string()).default([]),
  run_instructions: z.string().nullable().optional(),
  entry_points: z.array(z.string()).default([]),
});
export type ArchitectureResponse = z.infer<typeof ArchitectureResponseSchema>;

// ==========================================
// 6. Issues & Triage
// ==========================================
export const IssueAnalysisSchema = z.object({
  id: z.string(),
  type: z.string().nullable().optional(),
  severity: z.string().nullable().optional(),
  labels: z.array(z.string()).default([]),
  summary: z.string().nullable().optional(),
  missing_info: z.array(z.string()).default([]),
  duplicates: z.array(z.record(z.string(), z.any())).default([]),
  good_first_issue_score: z.number().nullable().optional(),
  suggested_reply: z.string().nullable().optional(),
  confidence: z.number().nullable().optional(),
  model: z.string(),
  prompt_version: z.string(),
  created_at: z.string(),
});
export type IssueAnalysis = z.infer<typeof IssueAnalysisSchema>;

export const IssueDetailSchema = z.object({
  id: z.string(),
  repo_id: z.string(),
  number: z.number(),
  title: z.string(),
  body: z.string().nullable().optional(),
  state: z.string().default('open'),
  author: z.string().nullable().optional(),
  labels: z.array(z.string()).default([]),
  html_url: z.string().nullable().optional(),
  triage_status: z.string().default('untriaged'),
  created_at_gh: z.string().nullable().optional(),
  analysis: IssueAnalysisSchema.nullable().optional(),
});
export type IssueDetail = z.infer<typeof IssueDetailSchema>;

export const IssueListResponseSchema = z.object({
  total: z.number().default(0),
  page: z.number().default(1),
  page_size: z.number().default(20),
  items: z.array(IssueDetailSchema).default([]),
});
export type IssueListResponse = z.infer<typeof IssueListResponseSchema>;

// ==========================================
// 7. Pull Requests & Reviews
// ==========================================
export const PRReviewSchema = z.object({
  id: z.string(),
  pr_id: z.string(),
  status: z.string(),
  summary: z.array(z.string()).default([]),
  risk_level: z.string().nullable().optional(),
  risk_reasons: z.array(z.string()).default([]),
  checks: z.record(z.string(), z.boolean().nullable().optional()).default({}),
  file_comments: z.array(z.record(z.string(), z.any())).default([]),
  newcomer_explainer: z.string().nullable().optional(),
  verdict: z.string().nullable().optional(),
  model: z.string(),
  prompt_version: z.string(),
  created_at: z.string(),
});
export type PRReview = z.infer<typeof PRReviewSchema>;

export const SpamAssessmentSchema = z.object({
  id: z.string(),
  pr_id: z.string(),
  spam_score: z.number().default(0),
  reasons: z.array(z.string()).default([]),
  rule_signals: z.record(z.string(), z.any()).default({}),
  recommended_action: z.string().nullable().optional(),
  polite_comment: z.string().nullable().optional(),
  created_at: z.string(),
});
export type SpamAssessment = z.infer<typeof SpamAssessmentSchema>;

export const PRDetailSchema = z.object({
  id: z.string(),
  repo_id: z.string(),
  number: z.number(),
  title: z.string(),
  body: z.string().nullable().optional(),
  state: z.string().default('open'),
  author: z.string().nullable().optional(),
  author_is_first_time: z.boolean().default(false),
  additions: z.number().default(0),
  deletions: z.number().default(0),
  changed_files: z.number().default(0),
  html_url: z.string().nullable().optional(),
  created_at_gh: z.string().nullable().optional(),
  review: PRReviewSchema.nullable().optional(),
  spam_assessment: SpamAssessmentSchema.nullable().optional(),
});
export type PRDetail = z.infer<typeof PRDetailSchema>;

export const PRListResponseSchema = z.array(PRDetailSchema);
export type PRListResponse = z.infer<typeof PRListResponseSchema>;

// ==========================================
// 8. Audit Log
// ==========================================
export const AuditItemSchema = z.object({
  id: z.string(),
  ts: z.string(),
  feature: z.string(),
  repo_id: z.string().nullable().optional(),
  ref_type: z.string().nullable().optional(),
  ref_id: z.string().nullable().optional(),
  action: z.string(),
  model: z.string().nullable().optional(),
  prompt_version: z.string().nullable().optional(),
  tokens_in: z.number().nullable().optional(),
  tokens_out: z.number().nullable().optional(),
  latency_ms: z.number().nullable().optional(),
  outcome: z.string().default('ok'),
  undo_payload: z.record(z.string(), z.any()).nullable().optional(),
  undone: z.boolean().default(false),
});
export type AuditItem = z.infer<typeof AuditItemSchema>;

export const AuditListResponseSchema = z.object({
  items: z.array(AuditItemSchema).default([]),
  total: z.number().default(0),
  page: z.number().default(1),
  page_size: z.number().default(20),
  pages: z.number().default(1),
});
export type AuditListResponse = z.infer<typeof AuditListResponseSchema>;

// ==========================================
// 9. Benchmarks
// ==========================================
export const BenchmarkRunSchema = z.object({
  id: z.string(),
  model: z.string(),
  sample_count: z.number().default(0),
  type_accuracy: z.number().nullable().optional(),
  severity_accuracy: z.number().nullable().optional(),
  json_valid_rate: z.number().nullable().optional(),
  avg_latency_ms: z.number().nullable().optional(),
  tokens_per_sec: z.number().nullable().optional(),
  details: z.record(z.string(), z.any()).nullable().optional(),
  status: z.string(),
  created_at: z.string().nullable().optional(),
});
export type BenchmarkRun = z.infer<typeof BenchmarkRunSchema>;

export const BenchmarkListResponseSchema = z.array(BenchmarkRunSchema);
export type BenchmarkListResponse = z.infer<typeof BenchmarkListResponseSchema>;
