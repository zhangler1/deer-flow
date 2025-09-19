export interface ModelConfig {
  basic: string[];
  reasoning: string[];
}

export interface RagConfig {
  provider: string;
}

export interface CustomSearchRepositoryConfig {
  id: string;
  name: string;
  description: string;
  repository: string;
}

export interface DeerFlowConfig {
  rag: RagConfig;
  models: ModelConfig;
  custom_search_repositories: CustomSearchRepositoryConfig[];
}
