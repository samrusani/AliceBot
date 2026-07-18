"""Governance and integration legacy-store carrier."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from psycopg.types.json import Jsonb

if TYPE_CHECKING:
    from alicebot_api.store import (
        ConsentRow,
        PolicyRow,
        ToolRow,
        ApprovalRow,
        TaskRow,
        GmailAccountRow,
        ProtectedGmailCredentialRow,
        CalendarAccountRow,
        ProtectedCalendarCredentialRow,
        JsonObject,
    )

INSERT_CONSENT_SQL = """
                INSERT INTO consents (
                  user_id,
                  consent_key,
                  status,
                  metadata,
                  created_at,
                  updated_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, clock_timestamp(), clock_timestamp())
                RETURNING id, user_id, consent_key, status, metadata, created_at, updated_at
                """

GET_CONSENT_BY_KEY_SQL = """
                SELECT id, user_id, consent_key, status, metadata, created_at, updated_at
                FROM consents
                WHERE consent_key = %s
                """

LIST_CONSENTS_SQL = """
                SELECT id, user_id, consent_key, status, metadata, created_at, updated_at
                FROM consents
                ORDER BY consent_key ASC, created_at ASC, id ASC
                """

UPDATE_CONSENT_SQL = """
                UPDATE consents
                SET status = %s,
                    metadata = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING id, user_id, consent_key, status, metadata, created_at, updated_at
                """

INSERT_POLICY_SQL = """
                INSERT INTO policies (
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, %s, %s, %s, %s, %s, clock_timestamp(), clock_timestamp())
                RETURNING
                  id,
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                """

GET_POLICY_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                WHERE id = %s
                """

LIST_POLICIES_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                ORDER BY priority ASC, created_at ASC, id ASC
                """

LIST_ACTIVE_POLICIES_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                WHERE active = TRUE
                ORDER BY priority ASC, created_at ASC, id ASC
                """

LIST_ACTIVE_POLICIES_FOR_PROFILE_SQL = """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                WHERE active = TRUE
                  AND (agent_profile_id IS NULL OR agent_profile_id = %s)
                ORDER BY priority ASC, created_at ASC, id ASC
                """

INSERT_TOOL_SQL = """
                INSERT INTO tools (
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
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
                  %s,
                  %s,
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                """

GET_TOOL_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                FROM tools
                WHERE id = %s
                """

LIST_TOOLS_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                FROM tools
                ORDER BY tool_key ASC, version ASC, created_at ASC, id ASC
                """

LIST_ACTIVE_TOOLS_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                FROM tools
                WHERE active = TRUE
                ORDER BY tool_key ASC, version ASC, created_at ASC, id ASC
                """

INSERT_APPROVAL_SQL = """
                INSERT INTO approvals (
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
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
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

GET_APPROVAL_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                FROM approvals
                WHERE id = %s
                """

LIST_APPROVALS_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                FROM approvals
                ORDER BY created_at ASC, id ASC
                """

UPDATE_APPROVAL_RESOLUTION_SQL = """
                UPDATE approvals
                SET status = %s,
                    resolved_at = clock_timestamp(),
                    resolved_by_user_id = app.current_user_id()
                WHERE id = %s
                  AND status = 'pending'
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

UPDATE_APPROVAL_TASK_STEP_SQL = """
                UPDATE approvals
                SET task_step_id = %s
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

UPDATE_APPROVAL_TASK_RUN_SQL = """
                UPDATE approvals
                SET task_run_id = %s
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

INSERT_TASK_SQL = """
                INSERT INTO tasks (
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
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
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

GET_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                FROM tasks
                WHERE id = %s
                """

GET_TASK_BY_APPROVAL_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                FROM tasks
                WHERE latest_approval_id = %s
                """

LIST_TASKS_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                FROM tasks
                ORDER BY created_at ASC, id ASC
                """

UPDATE_TASK_STATUS_BY_APPROVAL_SQL = """
                UPDATE tasks
                SET status = %s,
                    updated_at = clock_timestamp()
                WHERE latest_approval_id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL = """
                UPDATE tasks
                SET status = %s,
                    latest_execution_id = %s,
                    updated_at = clock_timestamp()
                WHERE latest_approval_id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

UPDATE_TASK_STATUS_SQL = """
                UPDATE tasks
                SET status = %s,
                    latest_approval_id = %s,
                    latest_execution_id = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

INSERT_GMAIL_ACCOUNT_SQL = """
                INSERT INTO gmail_accounts (
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                """

INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL = """
                INSERT INTO gmail_account_credentials (
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                """

GET_GMAIL_ACCOUNT_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM gmail_accounts
                WHERE id = %s
                """

GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM gmail_accounts
                WHERE provider_account_id = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """

GET_GMAIL_ACCOUNT_CREDENTIAL_SQL = """
                SELECT
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                FROM gmail_account_credentials
                WHERE gmail_account_id = %s
                """

UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL = """
                UPDATE gmail_account_credentials
                SET
                  auth_kind = %s,
                  credential_kind = %s,
                  secret_manager_kind = %s,
                  secret_ref = %s,
                  credential_blob = %s,
                  updated_at = clock_timestamp()
                WHERE gmail_account_id = %s
                RETURNING
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                """

LIST_GMAIL_ACCOUNTS_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM gmail_accounts
                ORDER BY created_at ASC, id ASC
                """

INSERT_CALENDAR_ACCOUNT_SQL = """
                INSERT INTO calendar_accounts (
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                """

INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL = """
                INSERT INTO calendar_account_credentials (
                  calendar_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  calendar_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                """

GET_CALENDAR_ACCOUNT_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM calendar_accounts
                WHERE id = %s
                """

GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM calendar_accounts
                WHERE provider_account_id = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """

GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL = """
                SELECT
                  calendar_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                FROM calendar_account_credentials
                WHERE calendar_account_id = %s
                """

LIST_CALENDAR_ACCOUNTS_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM calendar_accounts
                ORDER BY created_at ASC, id ASC
                """

__all__ = [
    'INSERT_CONSENT_SQL',
    'GET_CONSENT_BY_KEY_SQL',
    'LIST_CONSENTS_SQL',
    'UPDATE_CONSENT_SQL',
    'INSERT_POLICY_SQL',
    'GET_POLICY_SQL',
    'LIST_POLICIES_SQL',
    'LIST_ACTIVE_POLICIES_SQL',
    'LIST_ACTIVE_POLICIES_FOR_PROFILE_SQL',
    'INSERT_TOOL_SQL',
    'GET_TOOL_SQL',
    'LIST_TOOLS_SQL',
    'LIST_ACTIVE_TOOLS_SQL',
    'INSERT_APPROVAL_SQL',
    'GET_APPROVAL_SQL',
    'LIST_APPROVALS_SQL',
    'UPDATE_APPROVAL_RESOLUTION_SQL',
    'UPDATE_APPROVAL_TASK_STEP_SQL',
    'UPDATE_APPROVAL_TASK_RUN_SQL',
    'INSERT_TASK_SQL',
    'GET_TASK_SQL',
    'GET_TASK_BY_APPROVAL_SQL',
    'LIST_TASKS_SQL',
    'UPDATE_TASK_STATUS_BY_APPROVAL_SQL',
    'UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL',
    'UPDATE_TASK_STATUS_SQL',
    'INSERT_GMAIL_ACCOUNT_SQL',
    'INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL',
    'GET_GMAIL_ACCOUNT_SQL',
    'GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL',
    'GET_GMAIL_ACCOUNT_CREDENTIAL_SQL',
    'UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL',
    'LIST_GMAIL_ACCOUNTS_SQL',
    'INSERT_CALENDAR_ACCOUNT_SQL',
    'INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL',
    'GET_CALENDAR_ACCOUNT_SQL',
    'GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL',
    'GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL',
    'LIST_CALENDAR_ACCOUNTS_SQL',
]

def create_consent(
    self,
    *,
    consent_key: str,
    status: str,
    metadata: JsonObject,
) -> ConsentRow:
    return self._fetch_one(
        "create_consent",
        INSERT_CONSENT_SQL,
        (consent_key, status, Jsonb(metadata)),
    )

def get_consent_by_key_optional(self, consent_key: str) -> ConsentRow | None:
    return self._fetch_optional_one(GET_CONSENT_BY_KEY_SQL, (consent_key,))

def list_consents(self) -> list[ConsentRow]:
    return self._fetch_all(LIST_CONSENTS_SQL)

def update_consent(
    self,
    *,
    consent_id: UUID,
    status: str,
    metadata: JsonObject,
) -> ConsentRow:
    return self._fetch_one(
        "update_consent",
        UPDATE_CONSENT_SQL,
        (status, Jsonb(metadata), consent_id),
    )

def create_policy(
    self,
    *,
    agent_profile_id: str | None = None,
    name: str,
    action: str,
    scope: str,
    effect: str,
    priority: int,
    active: bool,
    conditions: JsonObject,
    required_consents: list[str],
) -> PolicyRow:
    return self._fetch_one(
        "create_policy",
        INSERT_POLICY_SQL,
        (
            agent_profile_id,
            name,
            action,
            scope,
            effect,
            priority,
            active,
            Jsonb(conditions),
            Jsonb(required_consents),
        ),
    )

def get_policy_optional(self, policy_id: UUID) -> PolicyRow | None:
    return self._fetch_optional_one(GET_POLICY_SQL, (policy_id,))

def list_policies(self) -> list[PolicyRow]:
    return self._fetch_all(LIST_POLICIES_SQL)

def list_active_policies(self, *, agent_profile_id: str | None = None) -> list[PolicyRow]:
    if agent_profile_id is None:
        return self._fetch_all(LIST_ACTIVE_POLICIES_SQL)
    return self._fetch_all(LIST_ACTIVE_POLICIES_FOR_PROFILE_SQL, (agent_profile_id,))

def create_tool(
    self,
    *,
    tool_key: str,
    name: str,
    description: str,
    version: str,
    metadata_version: str,
    active: bool,
    tags: list[str],
    action_hints: list[str],
    scope_hints: list[str],
    domain_hints: list[str],
    risk_hints: list[str],
    metadata: JsonObject,
) -> ToolRow:
    return self._fetch_one(
        "create_tool",
        INSERT_TOOL_SQL,
        (
            tool_key,
            name,
            description,
            version,
            metadata_version,
            active,
            Jsonb(tags),
            Jsonb(action_hints),
            Jsonb(scope_hints),
            Jsonb(domain_hints),
            Jsonb(risk_hints),
            Jsonb(metadata),
        ),
    )

def get_tool_optional(self, tool_id: UUID) -> ToolRow | None:
    return self._fetch_optional_one(GET_TOOL_SQL, (tool_id,))

def list_tools(self) -> list[ToolRow]:
    return self._fetch_all(LIST_TOOLS_SQL)

def list_active_tools(self) -> list[ToolRow]:
    return self._fetch_all(LIST_ACTIVE_TOOLS_SQL)

def create_approval(
    self,
    *,
    thread_id: UUID,
    tool_id: UUID,
    task_run_id: UUID | None = None,
    task_step_id: UUID | None = None,
    status: str,
    request: JsonObject,
    tool: JsonObject,
    routing: JsonObject,
    routing_trace_id: UUID,
) -> ApprovalRow:
    return self._fetch_one(
        "create_approval",
        INSERT_APPROVAL_SQL,
        (
            thread_id,
            tool_id,
            task_run_id,
            task_step_id,
            status,
            Jsonb(request),
            Jsonb(tool),
            Jsonb(routing),
            routing_trace_id,
        ),
    )

def get_approval_optional(self, approval_id: UUID) -> ApprovalRow | None:
    return self._fetch_optional_one(GET_APPROVAL_SQL, (approval_id,))

def list_approvals(self) -> list[ApprovalRow]:
    return self._fetch_all(LIST_APPROVALS_SQL)

def resolve_approval_optional(
    self,
    *,
    approval_id: UUID,
    status: str,
) -> ApprovalRow | None:
    return self._fetch_optional_one(
        UPDATE_APPROVAL_RESOLUTION_SQL,
        (status, approval_id),
    )

def update_approval_task_step_optional(
    self,
    *,
    approval_id: UUID,
    task_step_id: UUID,
) -> ApprovalRow | None:
    return self._fetch_optional_one(
        UPDATE_APPROVAL_TASK_STEP_SQL,
        (task_step_id, approval_id),
    )

def update_approval_task_run_optional(
    self,
    *,
    approval_id: UUID,
    task_run_id: UUID | None,
) -> ApprovalRow | None:
    return self._fetch_optional_one(
        UPDATE_APPROVAL_TASK_RUN_SQL,
        (task_run_id, approval_id),
    )

def create_task(
    self,
    *,
    thread_id: UUID,
    tool_id: UUID,
    status: str,
    request: JsonObject,
    tool: JsonObject,
    latest_approval_id: UUID | None,
    latest_execution_id: UUID | None,
) -> TaskRow:
    return self._fetch_one(
        "create_task",
        INSERT_TASK_SQL,
        (
            thread_id,
            tool_id,
            status,
            Jsonb(request),
            Jsonb(tool),
            latest_approval_id,
            latest_execution_id,
        ),
    )

def get_task_optional(self, task_id: UUID) -> TaskRow | None:
    return self._fetch_optional_one(GET_TASK_SQL, (task_id,))

def get_task_by_approval_optional(self, approval_id: UUID) -> TaskRow | None:
    return self._fetch_optional_one(GET_TASK_BY_APPROVAL_SQL, (approval_id,))

def list_tasks(self) -> list[TaskRow]:
    return self._fetch_all(LIST_TASKS_SQL)

def update_task_status_by_approval_optional(
    self,
    *,
    approval_id: UUID,
    status: str,
) -> TaskRow | None:
    return self._fetch_optional_one(
        UPDATE_TASK_STATUS_BY_APPROVAL_SQL,
        (status, approval_id),
    )

def update_task_execution_by_approval_optional(
    self,
    *,
    approval_id: UUID,
    latest_execution_id: UUID,
    status: str,
) -> TaskRow | None:
    return self._fetch_optional_one(
        UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL,
        (status, latest_execution_id, approval_id),
    )

def update_task_status_optional(
    self,
    *,
    task_id: UUID,
    status: str,
    latest_approval_id: UUID | None,
    latest_execution_id: UUID | None,
) -> TaskRow | None:
    return self._fetch_optional_one(
        UPDATE_TASK_STATUS_SQL,
        (status, latest_approval_id, latest_execution_id, task_id),
    )

def create_gmail_account(
    self,
    *,
    provider_account_id: str,
    email_address: str,
    display_name: str | None,
    scope: str,
) -> GmailAccountRow:
    return self._fetch_one(
        "create_gmail_account",
        INSERT_GMAIL_ACCOUNT_SQL,
        (provider_account_id, email_address, display_name, scope),
    )

def create_gmail_account_credential(
    self,
    *,
    gmail_account_id: UUID,
    auth_kind: str,
    credential_kind: str,
    secret_manager_kind: str,
    secret_ref: str | None,
    credential_blob: JsonObject | None,
) -> ProtectedGmailCredentialRow:
    return self._fetch_one(
        "create_gmail_account_credential",
        INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL,
        (
            gmail_account_id,
            auth_kind,
            credential_kind,
            secret_manager_kind,
            secret_ref,
            None if credential_blob is None else Jsonb(credential_blob),
        ),
    )

def get_gmail_account_optional(self, gmail_account_id: UUID) -> GmailAccountRow | None:
    return self._fetch_optional_one(GET_GMAIL_ACCOUNT_SQL, (gmail_account_id,))

def get_gmail_account_credential_optional(
    self,
    gmail_account_id: UUID,
) -> ProtectedGmailCredentialRow | None:
    return self._fetch_optional_one(GET_GMAIL_ACCOUNT_CREDENTIAL_SQL, (gmail_account_id,))

def update_gmail_account_credential(
    self,
    *,
    gmail_account_id: UUID,
    auth_kind: str,
    credential_kind: str,
    secret_manager_kind: str,
    secret_ref: str | None,
    credential_blob: JsonObject | None,
) -> ProtectedGmailCredentialRow:
    return self._fetch_one(
        "update_gmail_account_credential",
        UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL,
        (
            auth_kind,
            credential_kind,
            secret_manager_kind,
            secret_ref,
            None if credential_blob is None else Jsonb(credential_blob),
            gmail_account_id,
        ),
    )

def get_gmail_account_by_provider_account_id_optional(
    self,
    provider_account_id: str,
) -> GmailAccountRow | None:
    return self._fetch_optional_one(
        GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL,
        (provider_account_id,),
    )

def list_gmail_accounts(self) -> list[GmailAccountRow]:
    return self._fetch_all(LIST_GMAIL_ACCOUNTS_SQL)

def create_calendar_account(
    self,
    *,
    provider_account_id: str,
    email_address: str,
    display_name: str | None,
    scope: str,
) -> CalendarAccountRow:
    return self._fetch_one(
        "create_calendar_account",
        INSERT_CALENDAR_ACCOUNT_SQL,
        (provider_account_id, email_address, display_name, scope),
    )

def create_calendar_account_credential(
    self,
    *,
    calendar_account_id: UUID,
    auth_kind: str,
    credential_kind: str,
    secret_manager_kind: str,
    secret_ref: str | None,
    credential_blob: JsonObject | None,
) -> ProtectedCalendarCredentialRow:
    return self._fetch_one(
        "create_calendar_account_credential",
        INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL,
        (
            calendar_account_id,
            auth_kind,
            credential_kind,
            secret_manager_kind,
            secret_ref,
            None if credential_blob is None else Jsonb(credential_blob),
        ),
    )

def get_calendar_account_optional(self, calendar_account_id: UUID) -> CalendarAccountRow | None:
    return self._fetch_optional_one(GET_CALENDAR_ACCOUNT_SQL, (calendar_account_id,))

def get_calendar_account_credential_optional(
    self,
    calendar_account_id: UUID,
) -> ProtectedCalendarCredentialRow | None:
    return self._fetch_optional_one(
        GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL,
        (calendar_account_id,),
    )

def get_calendar_account_by_provider_account_id_optional(
    self,
    provider_account_id: str,
) -> CalendarAccountRow | None:
    return self._fetch_optional_one(
        GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL,
        (provider_account_id,),
    )

def list_calendar_accounts(self) -> list[CalendarAccountRow]:
    return self._fetch_all(LIST_CALENDAR_ACCOUNTS_SQL)
