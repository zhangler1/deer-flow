export interface ModelConfig {
  [key: string]: string[];
}

export interface ReporterOption {
  key: string;
  model: string;
}

export interface ReporterOptions {
  default: string;
  options: ReporterOption[];
}

export interface RagConfig {
  provider: string;
}

export interface DeerFlowConfig {
  rag: RagConfig;
  models: ModelConfig;
  reporter_options: ReporterOptions;
}
