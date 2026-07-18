"""Provider, embedding, semantic-retrieval, and entity legacy-store carrier."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from psycopg.types.json import Jsonb

if TYPE_CHECKING:
    from alicebot_api.store import (
        EmbeddingConfigRow,
        EntityEdgeRow,
        EntityRow,
        JsonObject,
        MemoryEmbeddingRow,
        ModelProviderRow,
        ProviderCapabilityRow,
        ProviderInvocationTelemetryRow,
        SemanticMemoryRetrievalRow,
        TaskArtifactChunkSemanticRetrievalRow,
        TaskBriefRow,
    )

INSERT_MODEL_PROVIDER_SQL = """
                INSERT INTO model_providers (
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata,
                  config_revision,
                  config_fingerprint_sha256,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  1,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata,
                  config_revision,
                  config_fingerprint_sha256,
                  created_at,
                  updated_at
                """

GET_MODEL_PROVIDER_FOR_WORKSPACE_SQL = """
                SELECT
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata,
                  config_revision,
                  config_fingerprint_sha256,
                  created_at,
                  updated_at
                FROM model_providers
                WHERE id = %s
                  AND workspace_id = %s
                """

LIST_MODEL_PROVIDERS_FOR_WORKSPACE_SQL = """
                SELECT
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata,
                  config_revision,
                  config_fingerprint_sha256,
                  created_at,
                  updated_at
                FROM model_providers
                WHERE workspace_id = %s
                ORDER BY created_at ASC, id ASC
                """

UPDATE_MODEL_PROVIDER_SQL = """
                UPDATE model_providers
                SET provider_key = %s,
                    model_provider = %s,
                    display_name = %s,
                    base_url = %s,
                    api_key = %s,
                    auth_mode = %s,
                    default_model = %s,
                    status = %s,
                    model_list_path = %s,
                    healthcheck_path = %s,
                    invoke_path = %s,
                    azure_api_version = %s,
                    azure_auth_secret_ref = %s,
                    metadata = %s,
                    config_revision = config_revision + 1,
                    config_fingerprint_sha256 = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                  AND workspace_id = %s
                  AND config_revision = %s
                  AND config_fingerprint_sha256 = %s
                RETURNING
                  id,
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata,
                  config_revision,
                  config_fingerprint_sha256,
                  created_at,
                  updated_at
                """

UPSERT_PROVIDER_CAPABILITY_IF_CURRENT_SQL = """
                WITH current_provider AS (
                  SELECT id, workspace_id, config_revision, config_fingerprint_sha256
                  FROM model_providers
                  WHERE id = %s
                    AND workspace_id = %s
                    AND config_revision = %s
                    AND config_fingerprint_sha256 = %s
                  FOR SHARE
                )
                INSERT INTO provider_capabilities (
                  workspace_id,
                  provider_id,
                  discovered_by_user_account_id,
                  adapter_key,
                  discovery_status,
                  capability_snapshot,
                  discovery_error,
                  provider_config_revision,
                  provider_config_fingerprint_sha256,
                  discovered_at,
                  created_at,
                  updated_at
                )
                SELECT
                  workspace_id,
                  id,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  config_revision,
                  config_fingerprint_sha256,
                  clock_timestamp(),
                  clock_timestamp(),
                  clock_timestamp()
                FROM current_provider
                ON CONFLICT (provider_id) DO UPDATE
                SET workspace_id = EXCLUDED.workspace_id,
                    discovered_by_user_account_id = EXCLUDED.discovered_by_user_account_id,
                    adapter_key = EXCLUDED.adapter_key,
                    discovery_status = EXCLUDED.discovery_status,
                    capability_snapshot = EXCLUDED.capability_snapshot,
                    discovery_error = EXCLUDED.discovery_error,
                    provider_config_revision = EXCLUDED.provider_config_revision,
                    provider_config_fingerprint_sha256 = EXCLUDED.provider_config_fingerprint_sha256,
                    discovered_at = EXCLUDED.discovered_at,
                    updated_at = clock_timestamp()
                RETURNING
                  id,
                  workspace_id,
                  provider_id,
                  discovered_by_user_account_id,
                  adapter_key,
                  discovery_status,
                  capability_snapshot,
                  discovery_error,
                  provider_config_revision,
                  provider_config_fingerprint_sha256,
                  discovered_at,
                  created_at,
                  updated_at
                """

GET_PROVIDER_CAPABILITY_FOR_PROVIDER_SQL = """
                SELECT
                  capability.id,
                  capability.workspace_id,
                  capability.provider_id,
                  capability.discovered_by_user_account_id,
                  capability.adapter_key,
                  capability.discovery_status,
                  capability.capability_snapshot,
                  capability.discovery_error,
                  capability.provider_config_revision,
                  capability.provider_config_fingerprint_sha256,
                  capability.discovered_at,
                  capability.created_at,
                  capability.updated_at
                FROM provider_capabilities AS capability
                JOIN model_providers AS provider
                  ON provider.id = capability.provider_id
                 AND provider.workspace_id = capability.workspace_id
                 AND provider.config_revision = capability.provider_config_revision
                 AND provider.config_fingerprint_sha256 = capability.provider_config_fingerprint_sha256
                WHERE capability.provider_id = %s
                  AND capability.workspace_id = %s
                """

IS_PROVIDER_SECRET_REFERENCE_IN_USE_SQL = """
                SELECT EXISTS (
                  SELECT 1
                  FROM model_providers
                  WHERE workspace_id = %s
                    AND (api_key = %s OR azure_auth_secret_ref = %s)
                ) AS in_use
                """

INSERT_PROVIDER_INVOCATION_TELEMETRY_SQL = """
                INSERT INTO provider_invocation_telemetry (
                  workspace_id,
                  provider_id,
                  thread_id,
                  invoked_by_user_account_id,
                  invocation_kind,
                  adapter_key,
                  runtime_provider,
                  requested_model,
                  response_model,
                  response_id,
                  status,
                  latency_ms,
                  usage,
                  error_detail,
                  created_at
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp()
                )
                RETURNING
                  id,
                  workspace_id,
                  provider_id,
                  thread_id,
                  invoked_by_user_account_id,
                  invocation_kind,
                  adapter_key,
                  runtime_provider,
                  requested_model,
                  response_model,
                  response_id,
                  status,
                  latency_ms,
                  usage,
                  error_detail,
                  created_at
                """

WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL = """
                SELECT 1
                FROM workspace_members
                WHERE workspace_id = %s
                  AND user_account_id = %s
                LIMIT 1
                """

INSERT_TASK_BRIEF_SQL = """
                INSERT INTO task_briefs (
                  user_id,
                  mode,
                  query_text,
                  scope,
                  provider_strategy,
                  model_pack_strategy,
                  token_budget,
                  estimated_tokens,
                  item_count,
                  deterministic_key,
                  payload,
                  created_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  mode,
                  query_text,
                  scope,
                  provider_strategy,
                  model_pack_strategy,
                  token_budget,
                  estimated_tokens,
                  item_count,
                  deterministic_key,
                  payload,
                  created_at
                """

GET_TASK_BRIEF_BY_ID_SQL = """
                SELECT
                  id,
                  user_id,
                  mode,
                  query_text,
                  scope,
                  provider_strategy,
                  model_pack_strategy,
                  token_budget,
                  estimated_tokens,
                  item_count,
                  deterministic_key,
                  payload,
                  created_at
                FROM task_briefs
                WHERE id = %s
                """

INSERT_EMBEDDING_CONFIG_SQL = """
                INSERT INTO embedding_configs (
                  user_id,
                  provider,
                  model,
                  version,
                  dimensions,
                  status,
                  metadata,
                  created_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, %s, %s, clock_timestamp())
                RETURNING id, user_id, provider, model, version, dimensions, status, metadata, created_at
                """

GET_EMBEDDING_CONFIG_SQL = """
                SELECT id, user_id, provider, model, version, dimensions, status, metadata, created_at
                FROM embedding_configs
                WHERE id = %s
                """

GET_EMBEDDING_CONFIG_BY_IDENTITY_SQL = """
                SELECT id, user_id, provider, model, version, dimensions, status, metadata, created_at
                FROM embedding_configs
                WHERE provider = %s
                  AND model = %s
                  AND version = %s
                """

LIST_EMBEDDING_CONFIGS_SQL = """
                SELECT id, user_id, provider, model, version, dimensions, status, metadata, created_at
                FROM embedding_configs
                ORDER BY created_at ASC, id ASC
                """

INSERT_MEMORY_EMBEDDING_SQL = """
                INSERT INTO memory_embeddings (
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, clock_timestamp(), clock_timestamp())
                RETURNING
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                """

GET_MEMORY_EMBEDDING_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE id = %s
                """

GET_MEMORY_EMBEDDING_BY_MEMORY_AND_CONFIG_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE memory_id = %s
                  AND embedding_config_id = %s
                """

LIST_MEMORY_EMBEDDINGS_FOR_MEMORY_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE memory_id = %s
                ORDER BY created_at ASC, id ASC
                """

LIST_MEMORY_EMBEDDINGS_FOR_CONFIG_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE embedding_config_id = %s
                ORDER BY created_at ASC, id ASC
                """

UPDATE_MEMORY_EMBEDDING_SQL = """
                UPDATE memory_embeddings
                SET dimensions = %s,
                    vector = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                """

RETRIEVE_SEMANTIC_MEMORY_MATCHES_SQL = """
                SELECT
                  memories.id,
                  memories.user_id,
                  memories.agent_profile_id,
                  memories.memory_key,
                  memories.value,
                  memories.status,
                  memories.source_event_ids,
                  memories.memory_type,
                  memories.confidence,
                  memories.salience,
                  memories.confirmation_status,
                  memories.trust_class,
                  memories.promotion_eligibility,
                  memories.evidence_count,
                  memories.independent_source_count,
                  memories.extracted_by_model,
                  memories.trust_reason,
                  memories.valid_from,
                  memories.valid_to,
                  memories.last_confirmed_at,
                  memories.created_at,
                  memories.updated_at,
                  memories.deleted_at,
                  1 - (
                    replace(memory_embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM memory_embeddings
                JOIN memories
                  ON memories.id = memory_embeddings.memory_id
                 AND memories.user_id = memory_embeddings.user_id
                WHERE memory_embeddings.embedding_config_id = %s
                  AND memory_embeddings.dimensions = %s
                  AND memories.status = 'active'
                ORDER BY score DESC, memories.created_at ASC, memories.id ASC
                LIMIT %s
                """

RETRIEVE_SEMANTIC_MEMORY_MATCHES_FOR_PROFILE_SQL = """
                SELECT
                  memories.id,
                  memories.user_id,
                  memories.agent_profile_id,
                  memories.memory_key,
                  memories.value,
                  memories.status,
                  memories.source_event_ids,
                  memories.memory_type,
                  memories.confidence,
                  memories.salience,
                  memories.confirmation_status,
                  memories.trust_class,
                  memories.promotion_eligibility,
                  memories.evidence_count,
                  memories.independent_source_count,
                  memories.extracted_by_model,
                  memories.trust_reason,
                  memories.valid_from,
                  memories.valid_to,
                  memories.last_confirmed_at,
                  memories.created_at,
                  memories.updated_at,
                  memories.deleted_at,
                  1 - (
                    replace(memory_embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM memory_embeddings
                JOIN memories
                  ON memories.id = memory_embeddings.memory_id
                 AND memories.user_id = memory_embeddings.user_id
                WHERE memory_embeddings.embedding_config_id = %s
                  AND memory_embeddings.dimensions = %s
                  AND memories.status = 'active'
                  AND memories.agent_profile_id = %s
                ORDER BY score DESC, memories.created_at ASC, memories.id ASC
                LIMIT %s
                """

RETRIEVE_TASK_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL = """
                SELECT
                  chunks.id,
                  chunks.user_id,
                  artifacts.task_id,
                  artifacts.id AS task_artifact_id,
                  artifacts.relative_path,
                  artifacts.media_type_hint,
                  chunks.sequence_no,
                  chunks.char_start,
                  chunks.char_end_exclusive,
                  chunks.text,
                  chunks.created_at,
                  chunks.updated_at,
                  embeddings.embedding_config_id,
                  1 - (
                    replace(embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                JOIN task_artifacts AS artifacts
                  ON artifacts.id = chunks.task_artifact_id
                 AND artifacts.user_id = chunks.user_id
                WHERE embeddings.embedding_config_id = %s
                  AND embeddings.dimensions = %s
                  AND artifacts.task_id = %s
                  AND artifacts.ingestion_status = 'ingested'
                ORDER BY score DESC, artifacts.relative_path ASC, chunks.sequence_no ASC, chunks.id ASC
                LIMIT %s
                """

RETRIEVE_ARTIFACT_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL = """
                SELECT
                  chunks.id,
                  chunks.user_id,
                  artifacts.task_id,
                  artifacts.id AS task_artifact_id,
                  artifacts.relative_path,
                  artifacts.media_type_hint,
                  chunks.sequence_no,
                  chunks.char_start,
                  chunks.char_end_exclusive,
                  chunks.text,
                  chunks.created_at,
                  chunks.updated_at,
                  embeddings.embedding_config_id,
                  1 - (
                    replace(embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                JOIN task_artifacts AS artifacts
                  ON artifacts.id = chunks.task_artifact_id
                 AND artifacts.user_id = chunks.user_id
                WHERE embeddings.embedding_config_id = %s
                  AND embeddings.dimensions = %s
                  AND artifacts.id = %s
                  AND artifacts.ingestion_status = 'ingested'
                ORDER BY score DESC, artifacts.relative_path ASC, chunks.sequence_no ASC, chunks.id ASC
                LIMIT %s
                """

INSERT_ENTITY_SQL = """
                INSERT INTO entities (user_id, entity_type, name, source_memory_ids, created_at)
                VALUES (app.current_user_id(), %s, %s, %s, clock_timestamp())
                RETURNING id, user_id, entity_type, name, source_memory_ids, created_at
                """

GET_ENTITY_SQL = """
                SELECT id, user_id, entity_type, name, source_memory_ids, created_at
                FROM entities
                WHERE id = %s
                """

LIST_ENTITIES_SQL = """
                SELECT id, user_id, entity_type, name, source_memory_ids, created_at
                FROM entities
                ORDER BY created_at ASC, id ASC
                """

INSERT_ENTITY_EDGE_SQL = """
                INSERT INTO entity_edges (
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, %s, %s, clock_timestamp())
                RETURNING
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                """

LIST_ENTITY_EDGES_FOR_ENTITY_SQL = """
                SELECT
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                FROM entity_edges
                WHERE from_entity_id = %s OR to_entity_id = %s
                ORDER BY created_at ASC, id ASC
                """

LIST_ENTITY_EDGES_FOR_ENTITIES_SQL = """
                SELECT
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                FROM entity_edges
                WHERE from_entity_id = ANY(%s) OR to_entity_id = ANY(%s)
                ORDER BY created_at ASC, id ASC
                """

__all__ = [
    "INSERT_MODEL_PROVIDER_SQL",
    "GET_MODEL_PROVIDER_FOR_WORKSPACE_SQL",
    "LIST_MODEL_PROVIDERS_FOR_WORKSPACE_SQL",
    "UPDATE_MODEL_PROVIDER_SQL",
    "UPSERT_PROVIDER_CAPABILITY_IF_CURRENT_SQL",
    "GET_PROVIDER_CAPABILITY_FOR_PROVIDER_SQL",
    "IS_PROVIDER_SECRET_REFERENCE_IN_USE_SQL",
    "INSERT_PROVIDER_INVOCATION_TELEMETRY_SQL",
    "WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL",
    "INSERT_TASK_BRIEF_SQL",
    "GET_TASK_BRIEF_BY_ID_SQL",
    "INSERT_EMBEDDING_CONFIG_SQL",
    "GET_EMBEDDING_CONFIG_SQL",
    "GET_EMBEDDING_CONFIG_BY_IDENTITY_SQL",
    "LIST_EMBEDDING_CONFIGS_SQL",
    "INSERT_MEMORY_EMBEDDING_SQL",
    "GET_MEMORY_EMBEDDING_SQL",
    "GET_MEMORY_EMBEDDING_BY_MEMORY_AND_CONFIG_SQL",
    "LIST_MEMORY_EMBEDDINGS_FOR_MEMORY_SQL",
    "LIST_MEMORY_EMBEDDINGS_FOR_CONFIG_SQL",
    "UPDATE_MEMORY_EMBEDDING_SQL",
    "RETRIEVE_SEMANTIC_MEMORY_MATCHES_SQL",
    "RETRIEVE_SEMANTIC_MEMORY_MATCHES_FOR_PROFILE_SQL",
    "RETRIEVE_TASK_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL",
    "RETRIEVE_ARTIFACT_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL",
    "INSERT_ENTITY_SQL",
    "GET_ENTITY_SQL",
    "LIST_ENTITIES_SQL",
    "INSERT_ENTITY_EDGE_SQL",
    "LIST_ENTITY_EDGES_FOR_ENTITY_SQL",
    "LIST_ENTITY_EDGES_FOR_ENTITIES_SQL",
]

def create_model_provider(
    self,
    *,
    workspace_id: UUID,
    created_by_user_account_id: UUID,
    provider_key: str,
    model_provider: str,
    display_name: str,
    base_url: str,
    api_key: str,
    default_model: str,
    status: str,
    metadata: JsonObject,
    auth_mode: str = "bearer",
    model_list_path: str = "",
    healthcheck_path: str = "",
    invoke_path: str = "",
    azure_api_version: str = "",
    azure_auth_secret_ref: str = "",
    config_fingerprint_sha256: str,
) -> ModelProviderRow:
    return self._fetch_one(
        "create_model_provider",
        INSERT_MODEL_PROVIDER_SQL,
        (
            workspace_id,
            created_by_user_account_id,
            provider_key,
            model_provider,
            display_name,
            base_url,
            api_key,
            auth_mode,
            default_model,
            status,
            model_list_path,
            healthcheck_path,
            invoke_path,
            azure_api_version,
            azure_auth_secret_ref,
            Jsonb(metadata),
            config_fingerprint_sha256,
        ),
    )

def get_model_provider_for_workspace_optional(
    self,
    *,
    provider_id: UUID,
    workspace_id: UUID,
) -> ModelProviderRow | None:
    return self._fetch_optional_one(
        GET_MODEL_PROVIDER_FOR_WORKSPACE_SQL,
        (provider_id, workspace_id),
    )

def list_model_providers_for_workspace(self, *, workspace_id: UUID) -> list[ModelProviderRow]:
    return self._fetch_all(
        LIST_MODEL_PROVIDERS_FOR_WORKSPACE_SQL,
        (workspace_id,),
    )

def update_model_provider(
    self,
    *,
    provider_id: UUID,
    workspace_id: UUID,
    provider_key: str,
    model_provider: str,
    display_name: str,
    base_url: str,
    api_key: str,
    auth_mode: str,
    default_model: str,
    status: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    azure_api_version: str,
    azure_auth_secret_ref: str,
    metadata: JsonObject,
    config_fingerprint_sha256: str,
    expected_config_revision: int,
    expected_config_fingerprint_sha256: str,
) -> ModelProviderRow | None:
    return self._fetch_optional_one(
        UPDATE_MODEL_PROVIDER_SQL,
        (
            provider_key,
            model_provider,
            display_name,
            base_url,
            api_key,
            auth_mode,
            default_model,
            status,
            model_list_path,
            healthcheck_path,
            invoke_path,
            azure_api_version,
            azure_auth_secret_ref,
            Jsonb(metadata),
            config_fingerprint_sha256,
            provider_id,
            workspace_id,
            expected_config_revision,
            expected_config_fingerprint_sha256,
        ),
    )

def upsert_provider_capability_if_current(
    self,
    *,
    workspace_id: UUID,
    provider_id: UUID,
    discovered_by_user_account_id: UUID,
    adapter_key: str,
    discovery_status: str,
    capability_snapshot: JsonObject,
    discovery_error: str | None,
    expected_config_revision: int,
    expected_config_fingerprint_sha256: str,
) -> ProviderCapabilityRow | None:
    return self._fetch_optional_one(
        UPSERT_PROVIDER_CAPABILITY_IF_CURRENT_SQL,
        (
            provider_id,
            workspace_id,
            expected_config_revision,
            expected_config_fingerprint_sha256,
            discovered_by_user_account_id,
            adapter_key,
            discovery_status,
            Jsonb(capability_snapshot),
            discovery_error,
        ),
    )

def get_provider_capability_for_provider_optional(
    self,
    *,
    provider_id: UUID,
    workspace_id: UUID,
) -> ProviderCapabilityRow | None:
    return self._fetch_optional_one(
        GET_PROVIDER_CAPABILITY_FOR_PROVIDER_SQL,
        (provider_id, workspace_id),
    )

def is_provider_secret_reference_in_use(
    self,
    *,
    workspace_id: UUID,
    encoded_reference: str,
) -> bool:
    row = self._fetch_one(
        "is_provider_secret_reference_in_use",
        IS_PROVIDER_SECRET_REFERENCE_IN_USE_SQL,
        (workspace_id, encoded_reference, encoded_reference),
    )
    return bool(row["in_use"])

def record_provider_invocation_telemetry(
    self,
    *,
    workspace_id: UUID,
    provider_id: UUID,
    thread_id: UUID | None,
    invoked_by_user_account_id: UUID,
    invocation_kind: str,
    adapter_key: str,
    runtime_provider: str,
    requested_model: str,
    response_model: str | None,
    response_id: str | None,
    status: str,
    latency_ms: int,
    usage: JsonObject,
    error_detail: str | None,
) -> ProviderInvocationTelemetryRow:
    return self._fetch_one(
        "record_provider_invocation_telemetry",
        INSERT_PROVIDER_INVOCATION_TELEMETRY_SQL,
        (
            workspace_id,
            provider_id,
            thread_id,
            invoked_by_user_account_id,
            invocation_kind,
            adapter_key,
            runtime_provider,
            requested_model,
            response_model,
            response_id,
            status,
            latency_ms,
            Jsonb(usage),
            error_detail,
        ),
    )

def workspace_visible_to_user_account(
    self,
    *,
    workspace_id: UUID,
    user_account_id: UUID,
) -> bool:
    with self.conn.cursor() as cur:
        cur.execute(
            WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL,
            (workspace_id, user_account_id),
        )
        return cur.fetchone() is not None

def create_task_brief(
    self,
    *,
    mode: str,
    query_text: str | None,
    scope: JsonObject,
    provider_strategy: str,
    model_pack_strategy: str,
    token_budget: int,
    estimated_tokens: int,
    item_count: int,
    deterministic_key: str,
    payload: JsonObject,
) -> TaskBriefRow:
    return self._fetch_one(
        "create_task_brief",
        INSERT_TASK_BRIEF_SQL,
        (
            mode,
            query_text,
            Jsonb(scope),
            provider_strategy,
            model_pack_strategy,
            token_budget,
            estimated_tokens,
            item_count,
            deterministic_key,
            Jsonb(payload),
        ),
    )

def get_task_brief_optional(self, *, task_brief_id: UUID) -> TaskBriefRow | None:
    return self._fetch_optional_one(
        GET_TASK_BRIEF_BY_ID_SQL,
        (task_brief_id,),
    )

def create_embedding_config(
    self,
    *,
    provider: str,
    model: str,
    version: str,
    dimensions: int,
    status: str,
    metadata: JsonObject,
) -> EmbeddingConfigRow:
    return self._fetch_one(
        "create_embedding_config",
        INSERT_EMBEDDING_CONFIG_SQL,
        (provider, model, version, dimensions, status, Jsonb(metadata)),
    )

def get_embedding_config_optional(self, embedding_config_id: UUID) -> EmbeddingConfigRow | None:
    return self._fetch_optional_one(GET_EMBEDDING_CONFIG_SQL, (embedding_config_id,))

def get_embedding_config_by_identity_optional(
    self,
    *,
    provider: str,
    model: str,
    version: str,
) -> EmbeddingConfigRow | None:
    return self._fetch_optional_one(
        GET_EMBEDDING_CONFIG_BY_IDENTITY_SQL,
        (provider, model, version),
    )

def list_embedding_configs(self) -> list[EmbeddingConfigRow]:
    return self._fetch_all(LIST_EMBEDDING_CONFIGS_SQL)

def create_memory_embedding(
    self,
    *,
    memory_id: UUID,
    embedding_config_id: UUID,
    dimensions: int,
    vector: list[float],
) -> MemoryEmbeddingRow:
    return self._fetch_one(
        "create_memory_embedding",
        INSERT_MEMORY_EMBEDDING_SQL,
        (memory_id, embedding_config_id, dimensions, Jsonb(vector)),
    )

def get_memory_embedding_optional(self, memory_embedding_id: UUID) -> MemoryEmbeddingRow | None:
    return self._fetch_optional_one(GET_MEMORY_EMBEDDING_SQL, (memory_embedding_id,))

def get_memory_embedding_by_memory_and_config_optional(
    self,
    *,
    memory_id: UUID,
    embedding_config_id: UUID,
) -> MemoryEmbeddingRow | None:
    return self._fetch_optional_one(
        GET_MEMORY_EMBEDDING_BY_MEMORY_AND_CONFIG_SQL,
        (memory_id, embedding_config_id),
    )

def list_memory_embeddings_for_memory(self, memory_id: UUID) -> list[MemoryEmbeddingRow]:
    return self._fetch_all(LIST_MEMORY_EMBEDDINGS_FOR_MEMORY_SQL, (memory_id,))

def list_memory_embeddings_for_config(
    self,
    embedding_config_id: UUID,
) -> list[MemoryEmbeddingRow]:
    return self._fetch_all(LIST_MEMORY_EMBEDDINGS_FOR_CONFIG_SQL, (embedding_config_id,))

def update_memory_embedding(
    self,
    *,
    memory_embedding_id: UUID,
    dimensions: int,
    vector: list[float],
) -> MemoryEmbeddingRow:
    return self._fetch_one(
        "update_memory_embedding",
        UPDATE_MEMORY_EMBEDDING_SQL,
        (dimensions, Jsonb(vector), memory_embedding_id),
    )

def retrieve_semantic_memory_matches(
    self,
    *,
    embedding_config_id: UUID,
    query_vector: list[float],
    limit: int,
) -> list[SemanticMemoryRetrievalRow]:
    return self._fetch_all(
        RETRIEVE_SEMANTIC_MEMORY_MATCHES_SQL,
        (
            self._vector_literal(query_vector),
            embedding_config_id,
            len(query_vector),
            limit,
        ),
    )

def retrieve_semantic_memory_matches_for_profile(
    self,
    *,
    embedding_config_id: UUID,
    query_vector: list[float],
    limit: int,
    agent_profile_id: str,
) -> list[SemanticMemoryRetrievalRow]:
    return self._fetch_all(
        RETRIEVE_SEMANTIC_MEMORY_MATCHES_FOR_PROFILE_SQL,
        (
            self._vector_literal(query_vector),
            embedding_config_id,
            len(query_vector),
            agent_profile_id,
            limit,
        ),
    )

def retrieve_task_scoped_semantic_artifact_chunk_matches(
    self,
    *,
    task_id: UUID,
    embedding_config_id: UUID,
    query_vector: list[float],
    limit: int,
) -> list[TaskArtifactChunkSemanticRetrievalRow]:
    return self._fetch_all(
        RETRIEVE_TASK_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL,
        (
            self._vector_literal(query_vector),
            embedding_config_id,
            len(query_vector),
            task_id,
            limit,
        ),
    )

def retrieve_artifact_scoped_semantic_artifact_chunk_matches(
    self,
    *,
    task_artifact_id: UUID,
    embedding_config_id: UUID,
    query_vector: list[float],
    limit: int,
) -> list[TaskArtifactChunkSemanticRetrievalRow]:
    return self._fetch_all(
        RETRIEVE_ARTIFACT_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL,
        (
            self._vector_literal(query_vector),
            embedding_config_id,
            len(query_vector),
            task_artifact_id,
            limit,
        ),
    )

def create_entity(
    self,
    *,
    entity_type: str,
    name: str,
    source_memory_ids: list[str],
) -> EntityRow:
    return self._fetch_one(
        "create_entity",
        INSERT_ENTITY_SQL,
        (entity_type, name, Jsonb(source_memory_ids)),
    )

def get_entity_optional(self, entity_id: UUID) -> EntityRow | None:
    return self._fetch_optional_one(GET_ENTITY_SQL, (entity_id,))

def list_entities(self) -> list[EntityRow]:
    return self._fetch_all(LIST_ENTITIES_SQL)

def create_entity_edge(
    self,
    *,
    from_entity_id: UUID,
    to_entity_id: UUID,
    relationship_type: str,
    valid_from: datetime | None,
    valid_to: datetime | None,
    source_memory_ids: list[str],
) -> EntityEdgeRow:
    return self._fetch_one(
        "create_entity_edge",
        INSERT_ENTITY_EDGE_SQL,
        (
            from_entity_id,
            to_entity_id,
            relationship_type,
            valid_from,
            valid_to,
            Jsonb(source_memory_ids),
        ),
    )

def list_entity_edges_for_entity(self, entity_id: UUID) -> list[EntityEdgeRow]:
    return self._fetch_all(LIST_ENTITY_EDGES_FOR_ENTITY_SQL, (entity_id, entity_id))

def list_entity_edges_for_entities(self, entity_ids: list[UUID]) -> list[EntityEdgeRow]:
    if not entity_ids:
        return []
    return self._fetch_all(LIST_ENTITY_EDGES_FOR_ENTITIES_SQL, (entity_ids, entity_ids))
