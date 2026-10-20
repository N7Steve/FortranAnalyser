export type FileStatus = 'ok' | 'partial' | 'failed' | 'skipped'
export interface Finding {
  rule: string
  path: string
  line: number
  severity: 'info' | 'warning' | 'error'
  message: string
}
export interface Metrics {
  physical_lines: number
  declarations: number
  declared_entities: number
  functions: number
  subroutines: number
  modules: number
  programs: number
  loops: number
  max_loop_depth: number
  calls: number
}
export interface Scope {
  name: string
  kind: string
  qualified_name: string
  line: number
  end_line: number
  implicit_none: boolean | null
  declarations: number
  declared_entities: number
  loops: number
  max_loop_depth: number
  calls: number
}
export interface SourceFile {
  path: string
  status: FileStatus
  source_form: string
  physical_lines: number | null
  metrics: Metrics | null
  scopes: Scope[]
  findings: Finding[]
}
export interface Report {
  schema_version: string
  rules_version: string
  parser: string
  files: SourceFile[]
  summary: {
    files: number
    ok: number
    partial: number
    failed: number
    skipped: number
    findings: number
  }
}
export interface Job {
  id: string
  name: string
  source_form: string
  status: 'uploading' | 'queued' | 'extracting' | 'running' | 'completed' | 'failed' | 'cancelled'
  processed: number
  total: number
  error: string | null
}
