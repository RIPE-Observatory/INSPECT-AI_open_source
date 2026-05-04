// Job / API domain types aligned with the latest backend job results payloads

export interface CostInfo {
  input_cost?: number;
  output_cost?: number;
  total_cost?: number;
  cost_breakdown?: string;
}

export interface TokenUsage {
  total_tokens?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  candidates_token_count?: number;
}

export interface JobData {
  id: string;
  status: string;
  identifier: string;
  results: JobResults | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  processing_time_seconds?: number | null;
  source?: string;
  external_id?: string | null;
  file_path?: string;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

export interface JobApiResponse extends ApiResponse<JobData> {
  job_id: string;
  filename: string;
}

export interface JobCreateResponse {
  job_id: string;
  filename: string;
}

export type JobStatusResponse = JobData;

export interface PDFViewerProps {
  jobId: string;
}

// Inspect-SR checklist payload
export interface InspectSRQuestion {
  label: string;
  automated_judgement: string | null;
  reviewed_judgement: string | null;
  comment: string;
  question_id: string;
}

export interface InspectSRProgress {
  total: number;
  percent: number;
  completed: number;
}

export interface InspectSRChecklist {
  data: InspectSRQuestion[];
  version: number;
  progress: InspectSRProgress;
  updated_at: string;
}

export interface InspectSRGetResponse {
  job_id: string;
  version: number;
  updated_at: string;
  progress: InspectSRProgress;
  data: InspectSRQuestion[];
}

export interface InspectSRPutRequest {
  data: InspectSRQuestion[];
  version?: number | null;
}

export interface InspectSRPutResponse {
  job_id: string;
  updated_at: string;
  version: number;
}

export interface InspectSRProgressResponse {
  job_id: string;
  completed: number;
  percent: number;
  total: number;
}

export type KgVisibility = "anonymous" | "public";

export interface ReviewerProfileResponse {
  id: string;
  clerk_user_id: string;
  given_name?: string | null;
  family_name?: string | null;
  username?: string | null;
  email?: string | null;
  affiliation_institution?: string | null;
  affiliation_department?: string | null;
  role?: string | null;
  country?: string | null;
  orcid?: string | null;
  onboarding_complete: boolean;
  kg_visibility: KgVisibility;
  kg_visibility_updated_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewerProfileRequest {
  given_name?: string | null;
  family_name?: string | null;
  username?: string | null;
  email?: string | null;
  affiliation_institution?: string | null;
  affiliation_department?: string | null;
  role?: string | null;
  country?: string | null;
  orcid?: string | null;
  onboarding_complete: boolean;
  kg_visibility?: KgVisibility;
}

// GROBID metadata summary
export interface GrobidMetadataSummary {
  total_references: number;
  references_with_dois: number;
  processing_time_seconds: number;
}

// Check 1 – LLM trial ID extraction
export interface Check1LLMExtraction {
  status: string;
  trial_id?: string;
  comment?: string;
  registry_type?: string;
  cost_info?: CostInfo;
  model_used?: string;
  token_usage?: TokenUsage;
}

// Check 2 – Registry lookup
export interface RegistryLookupResult {
  url?: string;
  registry_name?: string;
  lookup_successful?: boolean;
  trial_id_original?: string;
  study_first_submit_qc_date?: string;
  error_message?: string | null;
}

export interface Check2RegistryLookup {
  check_name: string;
  trial_id?: string;
  registry_type?: string;
  error_message?: string | null;
  lookup_results?: RegistryLookupResult;
}

// Check 3 – Study timeline dates
export interface StudyTimelineDateDetail {
  normalized_date?: string;
  interpretation_comment?: string;
}

export interface Check3StudyTimelineDates {
  status: string;
  cost_info?: CostInfo;
  model_used?: string;
  token_usage?: TokenUsage;
  study_end_date?: StudyTimelineDateDetail;
  recruitment_start?: StudyTimelineDateDetail;
  recruitment_finish?: StudyTimelineDateDetail;
}

// Check 4 – DOI extraction
export interface GrobidAuthor {
  name: string;
  surname?: string;
  forename?: string;
  lastname?: string;
  middle_name?: string;
  affiliations?: string[];
  is_corresponding: boolean;
  professional_title?: string | null;
}

export interface Check4DoiExtraction {
  status: string;
  comment?: string;
  extraction_method?: string;
  doi_value: string;
  main_title: string;
  main_authors: GrobidAuthor[];
  total_authors?: number;
  total_affiliations?: number;
  journal?: string;
  journal_abbrev?: string;
  publisher?: string;
  volume?: string;
  issue?: string;
  pages?: string;
  page_from?: string;
  page_to?: string;
  publication_date?: string;
  year?: string | number;
  issn?: string | null;
  eissn?: string | null;
}

// Check 5 – Reference DOI extraction
export interface GrobidReference {
  doi: string | null;
  title: string;
}

export interface Check5ReferenceDois {
  status: string;
  error_message?: string | null;
  reference_dois: string[];
  references_full: GrobidReference[];
}

// Check 6 – Prospective registration analysis
export interface Check6ProspectiveRegistrationAnalysis {
  status: string;
  message: string;
  check_name: string;
  is_prospective?: boolean;
  comparison_level?: string;
  llm_recruitment_start_raw?: string;
  registry_name_from_check2?: string;
  registry_registration_date_raw?: string;
  llm_recruitment_start_parsed_for_comparison?: string;
  registry_registration_date_parsed_for_comparison?: string;
}

// Check 7 – Retraction Watch
export interface RetractionWatchRecord {
  record_id?: number;
  title?: string;
  subject?: string;
  institution?: string;
  journal?: string;
  publisher?: string;
  country?: string;
  author?: string;
  urls?: string;
  article_type?: string;
  retraction_date?: string;
  retraction_doi?: string;
  retraction_pubmed_id?: number;
  original_paper_date?: string;
  original_paper_doi?: string;
  original_paper_pubmed_id?: number;
  retraction_nature?: string;
  reason?: string;
  paywalled?: string;
  notes?: string;
}

export interface RetractionLookupResult {
  searched_doi?: string | null;
  searched_title?: string | null;
  lookup_method?: string;
  found_in_database: boolean;
  retraction_record?: RetractionWatchRecord;
  error_message?: string;
}

export interface Check7RetractionWatch {
  check_name: string;
  csv_timestamp?: string;
  summary_message?: string;
  main_paper_result?: RetractionLookupResult;
  reference_results: RetractionLookupResult[];
}

// Check 7 (New) – Retraction Detection (INSPECT-SR 1.1)
export interface RetractionRecord {
  record_id: number;
  title: string;
  original_paper_doi: string | null;
  retraction_doi: string | null;
  retraction_nature: string;
  retraction_date: string | null;
  original_paper_date: string | null;
  journal: string | null;
  publisher: string | null;
  reason: string | null;
  authors: Array<{ name: string; position: number }>;
  // Additional fields from Retraction Watch database
  original_paper_pubmed_id?: string | null;
  retraction_pubmed_id?: string | null;
  country?: string | null;
  institution?: string | null;
  subject?: string | null;
  article_type?: string | null;
  notes?: string | null;
  urls?: string | null;
  paywalled?: string | null;
  author?: string | null;  // denormalized authors_fulltext field
}

export interface RetractionResult {
  found: boolean;
  searched_doi: string | null;
  searched_title: string | null;
  lookup_method: "doi" | "title" | "not_searched" | "unknown" | string;
  retractions: RetractionRecord[];
  error?: string;
}

export interface Check7RetractionDetection {
  main_article_result: RetractionResult | null;
  reference_results: RetractionResult[];
  summary: {
    main_article_retracted: boolean;
    references_checked: number;
    references_retracted: number;
    message: string;
  };
  error_message: string | null;
}

// Check 8 (New) – EOC/Correction Detection (INSPECT-SR 1.2)
export interface EOCNoticeRecord {
  record_id: number;
  title: string;
  original_paper_doi: string | null;
  retraction_doi: string | null;
  retraction_nature: string;
  retraction_date: string | null;
  original_paper_date: string | null;
  journal: string | null;
  publisher: string | null;
  reason: string | null;
  notes: string | null;
  authors: Array<{ name: string; position: number }>;
}

export interface EOCArticleResult {
  found: boolean;
  searched_doi: string | null;
  searched_title: string | null;
  lookup_method: string;
  notices: EOCNoticeRecord[];
  error?: string;
}

export interface Check8EOCCorrectionDetection {
  main_article_result: EOCArticleResult | null;
  summary: {
    main_article_has_eoc_or_correction: boolean;
    total_notices: number;
    message: string;
  };
  error_message: string | null;
}

// Check 9 (New) – Author Retraction History (INSPECT-SR 1.3)
export interface AuthorMetadata {
  forename: string | null;
  middle_name: string | null;
  surname: string | null;
  professional_title: string | null;
  affiliations: string[];
  is_corresponding: boolean;
}

export interface AuthorRetractionRecord {
  record_id: number;
  title: string;
  original_paper_doi: string | null;
  retraction_doi: string | null;
  retraction_nature: string;
  retraction_date: string | null;
  original_paper_date: string | null;
  journal: string | null;
  publisher: string | null;
  country: string | null;
  institution: string | null;
  subject: string | null;
  reason: string | null;
  authors: Array<{ name: string; position: number }>;
}

export interface AuthorResult {
  author_name: string;
  author_metadata: AuthorMetadata | null;
  has_retractions: boolean;
  retractions: AuthorRetractionRecord[];
  error: string | null;
}

export interface Check9AuthorRetractionHistory {
  author_results: AuthorResult[];
  summary: {
    total_authors_checked: number;
    authors_with_retractions: number;
    total_retractions_found: number;
    message: string;
  };
  error_message: string | null;
}

// PubPeer analysis
export interface PubPeerFeedback {
  id: string;
  url: string;
  title: string;
  users: string;
  updates: string[];
  journals: Array<{
    title: string;
    publisher: string;
  }>;
  total_comments: number;
  last_commented_at: string;
  peeriodical_links: string[];
  total_peeriodical_comments: number;
}

export interface PubPeerAPIResult {
  found: boolean;
  status?: string;
  feedbacks?: PubPeerFeedback[];
}

export interface PubPeerComment {
  id: number;
  date: string;
  links: string[];
  author: string;
  comment: string;
  is_reply: boolean;
  reply_to?: number;
  is_author_response: boolean;
}

export interface PubPeerPublicationStatus {
  link: string;
  status: string;
}

export interface PubPeerScrapedComments {
  comments: PubPeerComment[];
  publication_status: PubPeerPublicationStatus[];
}

export interface PubPeerLookupResult {
  doi: string;
  found: boolean;
  api_result?: PubPeerAPIResult;
  scraped_comments?: PubPeerScrapedComments;
  total_cost?: number;
  total_time?: number;
  error?: string;
}

export interface Check11PubpeerAnalysis {
  check_name: string;
  status: string;
  summary: Record<string, unknown>;
  processing_info?: Record<string, unknown> & {
    total_scraping_time_seconds?: number;
  };
  main_paper_result?: PubPeerLookupResult;
  reference_results: PubPeerLookupResult[];
  error_message?: string;
}

// Aggregated job results payload
// Normalized check envelope structure from backend
export interface CheckEnvelope<T = unknown> {
  status: "ok" | "concern" | "warning" | "pending" | "unknown" | "error" | "failed";
  summary: string;
  detail: string | null;
  check_id: string;
  finding_code: string;
  payload: T;
  dependencies?: string[];
  provider_messages?: string[];
  error_message?: string | null;
}

// Helper type for checks that include LLM costs
export interface CheckPayloadWithCost {
  cost_info?: CostInfo;
  model_used?: string;
  token_usage?: TokenUsage;
}

// Helper type for checks that include processing info (e.g., PubPeer)
export interface CheckPayloadWithProcessingInfo {
  processing_info?: {
    api_calls_made?: number;
    processing_time_seconds?: number;
    total_scraping_time_seconds?: number;
    [key: string]: unknown;
  };
}

export interface JobResults {
  inspect_sr?: InspectSRChecklist;
  grobid_metadata?: GrobidMetadataSummary;

  // New normalized checks structure (results.checks.{check_id})
  checks?: {
    trial_llm_extraction?: CheckEnvelope<Check1LLMExtraction>;
    registry_crosscheck?: CheckEnvelope<Check2RegistryLookup>;
    timeline_consistency?: CheckEnvelope<Check3StudyTimelineDates>;
    grobid_primary_metadata?: CheckEnvelope<Check4DoiExtraction>;
    grobid_reference_metadata?: CheckEnvelope<Check5ReferenceDois>;
    prospective_registration_analysis?: CheckEnvelope<Check6ProspectiveRegistrationAnalysis>;
    retraction_detection?: CheckEnvelope<Check7RetractionDetection>;
    eoc_correction_detection?: CheckEnvelope<Check8EOCCorrectionDetection>;
    author_retraction_history?: CheckEnvelope<Check9AuthorRetractionHistory>;
    pubpeer_signal_analysis?: CheckEnvelope<Check11PubpeerAnalysis>;
    [key: string]: CheckEnvelope<any> | undefined;
  };

  // Normalized sections structure (results.sections.{section_id})
  sections?: {
    retraction?: any;
    registration?: any;
    pubpeer?: any;
    [key: string]: any;
  };

  // Legacy check fields (deprecated, kept for backwards compatibility)
  check_1_llm_extraction?: Check1LLMExtraction;
  check_2_registry_lookup?: Check2RegistryLookup;
  check_3_study_timeline_dates?: Check3StudyTimelineDates;
  check_4_doi_extraction?: Check4DoiExtraction;
  check_5_reference_dois?: Check5ReferenceDois;
  check_6_prospective_registration_analysis?: Check6ProspectiveRegistrationAnalysis;
  check_7_retraction_watch?: Check7RetractionWatch;
  check_11_pubpeer_analysis?: Check11PubpeerAnalysis;

  [key: string]: unknown;
}

// Shared props for tab content components
export interface TabContentCommonProps {
  results: JobResults | null | undefined;
  jobStatus: JobData["status"] | undefined;
}

// Plot Modal Component Types
export interface PlotModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFocus: () => void;
  plotUrl: string;
  plotTitle: string;
  plotId: string;
  zIndex: number;
}
