"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import type {
  ApiSource,
  JsonObject,
  VNextArtifactQualityEvalRecord,
  VNextArtifactRecord,
  VNextBeliefRecord,
  VNextBrainCharterRecord,
  VNextConnectorHealthRecord,
  VNextContextPack,
  VNextDogfoodingDashboard,
  VNextDoctorPayload,
  VNextEventRecord,
  VNextMemoryRecord,
  VNextOpenLoopRecord,
  VNextPersonRecord,
  VNextPolicyTelemetrySummary,
  VNextProjectDashboard,
  VNextProjectRecord,
  VNextSchedulerStatus,
  VNextSourceRecord,
  VNextSourceTracePayload,
  VNextTaskRecord,
  VNextWorkspacePayload,
} from "../lib/api";
import {
  clearVNextOperatorAgentApiKey,
  confirmVNextMemory,
  createVNextContextPack,
  createVNextOpenLoop,
  createVNextProject,
  createVNextSource,
  captureVNextBrowserClip,
  generateVNextDailyBrief,
  generateVNextProjectUpdate,
  generateVNextWeeklySynthesis,
  getVNextWorkspace,
  patchVNextSchedulerWorkflow,
  rateVNextArtifactQuality,
  reviewVNextArtifact,
  reviewVNextMemory,
  reviewVNextOpenLoop,
  reviewVNextSource,
  runVNextDoctor,
  runVNextSchedulerDue,
  runVNextSchedulerWorkflowNow,
  setVNextOperatorAgentApiKey,
  syncVNextLocalFolderConnector,
  syncVNextTelegramConnector,
  updateVNextConnectorConfig,
  upsertVNextBrainCharter,
} from "../lib/api";
import { memoryProvenanceLabel } from "../lib/memory-provenance";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";
import {
  BROWSER_CLIPPER_BOOKMARKLET,
  COMPARISON_ARTIFACT_TYPES,
  FIXTURE_DOCTOR,
  INITIAL_CONNECTORS,
  VNEXT_DOMAIN_OPTIONS,
  VNEXT_SENSITIVITY_OPTIONS,
  type AskAnswer,
  type Domain,
  type Sensitivity,
  type VNextBrainWorkspaceProps,
  type WorkspaceView,
  agentDisplayName,
  agenticMemoryMetadata,
  answerFromContextPack,
  artifactExcerpt,
  artifactGenerationMode,
  artifactModelLabel,
  asDomain,
  asRecord,
  asSensitivity,
  connectorHealth,
  createSummary,
  domainLabel,
  emptyWorkspace,
  eventTitle,
  fixtureWorkspace,
  latestArtifact,
  latestArtifactByMode,
  memoryText,
  pushBoundedLog,
  scheduleSummary,
  scheduleValue,
  sensitivityLabel,
  sourceText,
  summarizeSources,
  textValue,
  workspaceFromPayload,
} from "./vnext-workspace-model";
import { VNextHomeMetrics, VNextSurfaceNavigation } from "./vnext-workspace-overview";

export {
  INITIAL_CONNECTORS,
  VNEXT_DOMAIN_OPTIONS,
  VNEXT_SENSITIVITY_OPTIONS,
  VNEXT_SUPPORTED_CONNECTOR_IDS,
  getVNextWorkspaceFixtureContract,
} from "./vnext-workspace-model";

export function VNextBrainWorkspace({
  apiBaseUrl,
  userId,
  initialSource = "fixture",
}: VNextBrainWorkspaceProps) {
  const liveModeReady = Boolean(apiBaseUrl && userId && initialSource === "live");
  const [workspace, setWorkspace] = useState<WorkspaceView>(() =>
    liveModeReady ? emptyWorkspace() : fixtureWorkspace(),
  );
  const [dataSource, setDataSource] = useState<ApiSource>(liveModeReady ? "live" : "fixture");
  const [isRefreshing, setIsRefreshing] = useState(liveModeReady);
  const [pendingAction, setPendingAction] = useState("");
  const [statusText, setStatusText] = useState(
    liveModeReady
      ? "Loading live vNext workspace from the local API."
      : "Demo mode is using fixture data. Add local API config to use live mode.",
  );
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [actionLog, setActionLog] = useState<string[]>([
    liveModeReady ? "Live workspace is default for this local configuration." : "Fixture demo mode is active.",
  ]);
  const [operatorAgentApiKey, setOperatorAgentApiKey] = useState("");
  const [operatorAgentApiKeyActive, setOperatorAgentApiKeyActive] = useState(false);

  const [captureTitle, setCaptureTitle] = useState("Launch note");
  const [captureText, setCaptureText] = useState(
    "Decision: Keep the launch cohort small.\nTodo: Confirm launch checklist owner before product review.",
  );
  const [defaultDomain, setDefaultDomain] = useState<Domain>("project");
  const [defaultSensitivity, setDefaultSensitivity] = useState<Sensitivity>("private");
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const selectedSource = useMemo(
    () => workspace.sources.find((source) => source.id === selectedSourceId) ?? workspace.sources[0] ?? null,
    [selectedSourceId, workspace.sources],
  );
  const selectedSourceTrace = useMemo(
    () =>
      selectedSource
        ? workspace.traceability.items.find((trace) => trace.summary.source_id === selectedSource.id) ?? null
        : null,
    [selectedSource, workspace.traceability.items],
  );
  const [sourceTitleDraft, setSourceTitleDraft] = useState("");
  const [sourceDomainDraft, setSourceDomainDraft] = useState<Domain>("project");
  const [sourceSensitivityDraft, setSourceSensitivityDraft] = useState<Sensitivity>("private");
  const [sourceProjectDraft, setSourceProjectDraft] = useState("");
  const [sourceReviewNote, setSourceReviewNote] = useState("Reviewed from /vnext operator console.");

  const [selectedReviewId, setSelectedReviewId] = useState("");
  const selectedReview = useMemo(
    () => workspace.reviewItems.find((item) => item.id === selectedReviewId) ?? workspace.reviewItems[0] ?? null,
    [selectedReviewId, workspace.reviewItems],
  );
  const [draftTitle, setDraftTitle] = useState("");
  const [draftText, setDraftText] = useState("");
  const [draftDomain, setDraftDomain] = useState<Domain>("project");
  const [draftSensitivity, setDraftSensitivity] = useState<Sensitivity>("private");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [inlineConfirmationDrafts, setInlineConfirmationDrafts] = useState<Record<string, string>>({});

  const [question, setQuestion] = useState("What should I focus on before the product review?");
  const [answer, setAnswer] = useState<AskAnswer>({
    question,
    summary:
      "Ask Alice will call the live context-pack endpoint when local API configuration is present.",
    memoriesUsed: [],
    contradictions: [],
    why: ["No retrieval has run yet in this session."],
    sources: [],
    domain: "project",
    sensitivity: "private",
  });

  const [openLoopTitle, setOpenLoopTitle] = useState("Confirm launch checklist owner");
  const [openLoopDescription, setOpenLoopDescription] = useState("Created from the selected memory candidate.");
  const [openLoopDueAt, setOpenLoopDueAt] = useState("");
  const [openLoopPriority, setOpenLoopPriority] = useState("normal");
  const [selectedOpenLoopId, setSelectedOpenLoopId] = useState("");

  const [newProjectName, setNewProjectName] = useState("Product launch");
  const [newProjectState, setNewProjectState] = useState("Launch ownership is unresolved.");

  const [charterText, setCharterText] = useState("# ALICE.md\n\nKeep generated artifacts reviewable before promotion.");
  const [charterSensitivity, setCharterSensitivity] = useState<Sensitivity>("private");
  const [schedulerDrafts, setSchedulerDrafts] = useState<
    Record<string, { timeOfDay: string; dayOfWeek: string; timezone: string }>
  >({});
  const [generationMode, setGenerationMode] = useState<"deterministic" | "model_backed">("deterministic");
  const [qualityArtifactId, setQualityArtifactId] = useState("");
  const [qualityScores, setQualityScores] = useState({
    usefulness: 4,
    accuracy: 4,
    source_grounding: 4,
    novel_connections: 3,
    actionability: 4,
    hallucination_risk: 1,
  });
  const [qualityVerbosity, setQualityVerbosity] = useState("right_sized");
  const [qualityComments, setQualityComments] = useState("");
  const [selectedConnectorId, setSelectedConnectorId] = useState("telegram");
  const [connectorEnabled, setConnectorEnabled] = useState(true);
  const [connectorDomain, setConnectorDomain] = useState<Domain>("personal");
  const [connectorSensitivity, setConnectorSensitivity] = useState<Sensitivity>("private");
  const [connectorSecretRef, setConnectorSecretRef] = useState("telegram.bot_token.default");
  const [telegramAllowedChats, setTelegramAllowedChats] = useState("999001");
  const [localFolderPath, setLocalFolderPath] = useState("~/Notes");
  const [localFolderExtensions, setLocalFolderExtensions] = useState(".md,.txt");
  const [localFolderIgnores, setLocalFolderIgnores] = useState("generated,.git,node_modules,.venv,.cache");
  const [browserClipUrl, setBrowserClipUrl] = useState("https://example.test/article");
  const [browserClipSelection, setBrowserClipSelection] = useState("Fact: Browser clipper test content remains untrusted.");

  const dailyArtifact = latestArtifact(workspace.artifacts, "daily_brief");
  const weeklyArtifact = latestArtifact(workspace.artifacts, "weekly_synthesis");
  const projectUpdateArtifacts = workspace.artifacts.filter((artifact) => artifact.artifact_type === "project_update");

  const refreshWorkspace = useCallback(
    async (successMessage?: string) => {
      if (!liveModeReady || !apiBaseUrl || !userId) {
        return;
      }
      setIsRefreshing(true);
      setStatusTone("info");
      setStatusText("Refreshing live vNext workspace...");
      try {
        const payload = await getVNextWorkspace(apiBaseUrl, userId);
        const nextWorkspace = workspaceFromPayload(payload);
        setWorkspace(nextWorkspace);
        setDataSource("live");
        setStatusTone("success");
        setStatusText(successMessage ?? "Live vNext workspace loaded.");
        setActionLog((previous) => pushBoundedLog(successMessage ?? "Live workspace refreshed.", previous));
      } catch (error) {
        setStatusTone("danger");
        setStatusText(`Unable to load live workspace: ${error instanceof Error ? error.message : "Request failed"}`);
        setDataSource("live");
      } finally {
        setIsRefreshing(false);
      }
    },
    [apiBaseUrl, liveModeReady, userId],
  );

  useEffect(
    () => () => {
      clearVNextOperatorAgentApiKey();
    },
    [],
  );

  useEffect(() => {
    if (liveModeReady) {
      void refreshWorkspace("Live vNext workspace loaded.");
    }
  }, [liveModeReady, refreshWorkspace]);

  useEffect(() => {
    if (selectedSource) {
      const metadata = asRecord(selectedSource.metadata_json);
      setSelectedSourceId(selectedSource.id);
      setSourceTitleDraft(textValue(selectedSource.title) || selectedSource.source_type);
      setSourceDomainDraft(asDomain(selectedSource.domain));
      setSourceSensitivityDraft(asSensitivity(selectedSource.sensitivity));
      setSourceProjectDraft(textValue(metadata.project_id) || workspace.projects[0]?.id || "");
    } else {
      setSelectedSourceId("");
      setSourceTitleDraft("");
      setSourceProjectDraft(workspace.projects[0]?.id ?? "");
    }
  }, [selectedSource, workspace.projects]);

  useEffect(() => {
    if (selectedReview) {
      setSelectedReviewId(selectedReview.id);
      setDraftTitle(textValue(selectedReview.title) || memoryText(selectedReview));
      setDraftText(memoryText(selectedReview));
      setDraftDomain(asDomain(selectedReview.domain));
      setDraftSensitivity(asSensitivity(selectedReview.sensitivity));
      const metadata = asRecord(selectedReview.metadata_json);
      setSelectedProjectId(textValue(metadata.project_id) || workspace.projects[0]?.id || "");
      setOpenLoopTitle(memoryText(selectedReview));
    } else {
      setSelectedReviewId("");
      setDraftTitle("");
      setDraftText("");
      setSelectedProjectId(workspace.projects[0]?.id ?? "");
    }
  }, [selectedReview, workspace.projects]);

  useEffect(() => {
    if (workspace.openLoops.length > 0 && !workspace.openLoops.some((loop) => loop.id === selectedOpenLoopId)) {
      setSelectedOpenLoopId(workspace.openLoops[0].id);
    }
  }, [selectedOpenLoopId, workspace.openLoops]);

  useEffect(() => {
    if (workspace.brainCharter) {
      setCharterText(workspace.brainCharter.content_markdown);
      setCharterSensitivity(asSensitivity(workspace.brainCharter.sensitivity));
    }
  }, [workspace.brainCharter]);

  useEffect(() => {
    const connector = INITIAL_CONNECTORS.find((item) => item.id === selectedConnectorId) ?? INITIAL_CONNECTORS[0];
    const health = workspace.connectorHealth.items.find((item) => item.connector_name === connector.id) ?? null;
    setConnectorEnabled(Boolean(health?.enabled ?? false));
    setConnectorDomain(asDomain(health?.default_domain ?? connector.defaultDomain));
    setConnectorSensitivity(asSensitivity(health?.default_sensitivity ?? connector.defaultSensitivity));
    if (connector.id === "telegram") {
      setConnectorSecretRef("telegram.bot_token.default");
    } else if (connector.id === "browser_clipper") {
      setConnectorSecretRef("browser.capture_token.default");
    } else {
      setConnectorSecretRef("");
    }
  }, [selectedConnectorId, workspace.connectorHealth]);

  function handleOperatorAgentApiKeyChange(value: string) {
    clearVNextOperatorAgentApiKey();
    setOperatorAgentApiKeyActive(false);
    setOperatorAgentApiKey(value);
  }

  async function handleOperatorAgentApiKeySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedAgentApiKey = operatorAgentApiKey.trim();
    if (!normalizedAgentApiKey) {
      clearVNextOperatorAgentApiKey();
      setOperatorAgentApiKeyActive(false);
      setStatusTone("danger");
      setStatusText("Enter an unbound admin_agent API key for the local operator session.");
      return;
    }

    setVNextOperatorAgentApiKey(normalizedAgentApiKey);
    setOperatorAgentApiKey("");
    setOperatorAgentApiKeyActive(true);
    setStatusTone("info");
    setStatusText("Operator key loaded into browser memory for this mounted session.");
    await refreshWorkspace("Live vNext workspace loaded with operator authentication.");
  }

  function handleClearOperatorAgentApiKey() {
    clearVNextOperatorAgentApiKey();
    setOperatorAgentApiKey("");
    setOperatorAgentApiKeyActive(false);
    setStatusTone("info");
    setStatusText("Operator key cleared from browser memory.");
  }

  function updateFixtureWorkspace(mutator: (previous: WorkspaceView) => WorkspaceView, message: string) {
    setWorkspace((previous) => mutator(previous));
    setStatusTone("success");
    setStatusText(message);
    setActionLog((previous) => pushBoundedLog(message, previous));
  }

  async function runLiveAction(label: string, action: () => Promise<void>, successMessage: string) {
    if (!liveModeReady || !apiBaseUrl || !userId) {
      setStatusTone("danger");
      setStatusText("Live write is unavailable without local API configuration. Use demo mode for fixture actions.");
      return;
    }
    setPendingAction(label);
    setStatusTone("info");
    setStatusText(label);
    try {
      await action();
      await refreshWorkspace(successMessage);
    } catch (error) {
      setStatusTone("danger");
      setStatusText(`${label} failed: ${error instanceof Error ? error.message : "Request failed"}`);
    } finally {
      setPendingAction("");
    }
  }

  async function handleCapture(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = captureText.trim();
    if (!text) {
      setStatusTone("danger");
      setStatusText("Enter source text before capture.");
      return;
    }

    if (!liveModeReady || !apiBaseUrl || !userId) {
      const nextSource: VNextSourceRecord = {
        id: `source-demo-${workspace.sources.length + 1}`,
        source_type: "manual_text",
        title: captureTitle.trim() || "Untitled note",
        captured_at: new Date().toISOString(),
        domain: defaultDomain,
        sensitivity: defaultSensitivity,
        metadata_json: { raw_text: text },
      };
      const nextMemory: VNextMemoryRecord = {
        id: `memory-demo-${workspace.reviewItems.length + 1}`,
        memory_key: `vnext.demo.${workspace.reviewItems.length + 1}`,
        memory_type: text.toLowerCase().includes("todo") ? "open_loop" : "semantic",
        status: "candidate",
        title: text.split("\n")[0]?.replace(/^(decision|fact|todo):\s*/i, "") || "Captured candidate",
        canonical_text: text.split("\n")[0]?.replace(/^(decision|fact|todo):\s*/i, "") || text,
        summary: text.slice(0, 280),
        domain: defaultDomain,
        sensitivity: defaultSensitivity,
        value: { text },
        metadata_json: { source_id: nextSource.id },
      };
      updateFixtureWorkspace(
        (previous) => {
          const view = {
            ...previous,
            sources: [nextSource, ...previous.sources],
            reviewItems: [nextMemory, ...previous.reviewItems],
          };
          return { ...view, summary: createSummary(view) };
        },
        "Demo source captured and candidate memory generated.",
      );
      setSelectedReviewId(nextMemory.id);
      setSelectedSourceId(nextSource.id);
      return;
    }

    await runLiveAction(
      "Capturing vNext source...",
      async () => {
        await createVNextSource(apiBaseUrl, {
          user_id: userId,
          raw_text: text,
          title: captureTitle.trim() || null,
          domain: defaultDomain,
          sensitivity: defaultSensitivity,
        });
      },
      "Source captured, chunked, and candidate memories refreshed.",
    );
  }

  async function askAlice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuestion = question.trim();
    if (!normalizedQuestion) {
      setStatusTone("danger");
      setStatusText("Ask Alice needs a question.");
      return;
    }

    if (!liveModeReady || !apiBaseUrl || !userId) {
      setAnswer({
        question: normalizedQuestion,
        summary: `For "${normalizedQuestion}", Alice would focus on launch ownership and vendor legal review in demo mode.`,
        memoriesUsed: workspace.reviewItems.slice(0, 3).map(memoryText),
        contradictions: ["One older note names Morgan as owner; the latest capture says ownership is not confirmed."],
        why: ["Demo mode ranks active open loops and project-matching memory candidates first."],
        sources: workspace.sources.map((source) => `source:${source.id}`),
        domain: defaultDomain,
        sensitivity: defaultSensitivity,
      });
      setActionLog((previous) => pushBoundedLog("Demo Ask Alice answer refreshed.", previous));
      return;
    }

    setPendingAction("Asking Alice...");
    try {
      const pack = await createVNextContextPack(apiBaseUrl, {
        user_id: userId,
        query: normalizedQuestion,
        scope: { domains: [defaultDomain] },
        options: {
          include_sources: true,
          include_contradictions: true,
          sensitivity_allowed: ["public", "internal", "private", "unknown"],
          max_items: 8,
        },
      });
      setAnswer(answerFromContextPack(normalizedQuestion, pack));
      await refreshWorkspace("Ask Alice context pack compiled with provenance.");
    } catch (error) {
      setStatusTone("danger");
      setStatusText(`Ask Alice failed: ${error instanceof Error ? error.message : "Request failed"}`);
    } finally {
      setPendingAction("");
    }
  }

  async function handleMemoryAction(action: "accept" | "edit" | "reject" | "private" | "assign_project" | "promote") {
    if (!selectedReview) {
      return;
    }

    if (!liveModeReady || !apiBaseUrl || !userId) {
      updateFixtureWorkspace(
        (previous) => {
          const nextItems = previous.reviewItems.map((item) =>
            item.id === selectedReview.id
              ? {
                  ...item,
                  title: draftTitle,
                  canonical_text: draftText,
                  summary: draftText.slice(0, 280),
                  domain: draftDomain,
                  sensitivity: action === "private" ? "private" : draftSensitivity,
                  status:
                    action === "reject"
                      ? "rejected"
                      : action === "private"
                        ? "private_only"
                        : action === "promote" || action === "accept" || action === "edit"
                          ? "active"
                          : item.status,
                  metadata_json: {
                    ...asRecord(item.metadata_json),
                    project_id: action === "assign_project" ? selectedProjectId : asRecord(item.metadata_json).project_id,
                  },
                }
              : item,
          );
          const view = { ...previous, reviewItems: nextItems };
          return { ...view, summary: createSummary(view) };
        },
        `Demo memory review action applied: ${action}.`,
      );
      return;
    }

    await runLiveAction(
      `Applying memory review action: ${action}...`,
      async () => {
        await reviewVNextMemory(apiBaseUrl, selectedReview.id, {
          user_id: userId,
          action,
          title: draftTitle,
          canonical_text: draftText,
          summary: draftText.slice(0, 280),
          domain: draftDomain,
          sensitivity: action === "private" ? "private" : draftSensitivity,
          project_id: action === "assign_project" ? selectedProjectId : undefined,
          reason: "Reviewed from live /vnext workspace.",
        });
      },
      `Memory review action applied: ${action}.`,
    );
  }

  async function handleInlineConfirmation(
    memory: VNextMemoryRecord,
    action: "confirm" | "edit" | "reject",
  ) {
    const agentic = agenticMemoryMetadata(memory);
    const confirmation = asRecord(agentic.confirmation);
    const confirmationId = textValue(confirmation.confirmation_id);
    const editedText = (inlineConfirmationDrafts[memory.id] ?? memoryText(memory)).trim();

    if (!confirmationId) {
      setStatusTone("danger");
      setStatusText("This inline confirmation is missing its confirmation ID and cannot be reviewed.");
      return;
    }
    if (action === "edit" && !editedText) {
      setStatusTone("danger");
      setStatusText("Enter revised memory text before saving and confirming the edit.");
      return;
    }

    if (!liveModeReady || !apiBaseUrl || !userId) {
      const now = new Date().toISOString();
      updateFixtureWorkspace(
        (previous) => {
          const updatedMemory: VNextMemoryRecord = {
            ...memory,
            canonical_text: action === "edit" ? editedText : memory.canonical_text,
            summary: action === "edit" ? editedText.slice(0, 280) : memory.summary,
            status: action === "reject" ? "rejected" : "active",
            confirmation_status: action === "reject" ? memory.confirmation_status : "confirmed",
            last_confirmed_at: action === "reject" ? memory.last_confirmed_at : now,
            metadata_json: {
              ...asRecord(memory.metadata_json),
              agentic_memory: {
                ...agentic,
                lifecycle_status: action === "reject" ? "confirmation_rejected" : "inline_confirmed",
                confirmation: {
                  ...confirmation,
                  status: action === "reject" ? "rejected" : "confirmed",
                },
              },
            },
          };
          return {
            ...previous,
            agentActivity: {
              ...previous.agentActivity,
              inline_confirmations: previous.agentActivity.inline_confirmations.filter(
                (item) => item.id !== memory.id,
              ),
              recent_commits:
                action === "reject"
                  ? previous.agentActivity.recent_commits
                  : [updatedMemory, ...previous.agentActivity.recent_commits].slice(0, 20),
            },
          };
        },
        `Demo inline confirmation action applied: ${action}.`,
      );
      setInlineConfirmationDrafts((previous) => {
        const next = { ...previous };
        delete next[memory.id];
        return next;
      });
      return;
    }

    await runLiveAction(
      `${action === "reject" ? "Rejecting" : action === "edit" ? "Editing and confirming" : "Confirming"} inline memory...`,
      async () => {
        await confirmVNextMemory(apiBaseUrl, {
          user_id: userId,
          confirmation_id: confirmationId,
          action,
          canonical_text: action === "edit" ? editedText : undefined,
          rationale: "Reviewed from the live /vnext operator console.",
        });
      },
      `Inline memory ${action === "reject" ? "rejected" : "confirmed"}.`,
    );
  }

  async function handleCreateOpenLoop() {
    const title = openLoopTitle.trim();
    if (!title) {
      setStatusTone("danger");
      setStatusText("Open-loop creation needs a title.");
      return;
    }

    if (!liveModeReady || !apiBaseUrl || !userId) {
      const nextLoop: VNextOpenLoopRecord = {
        id: `loop-demo-${workspace.openLoops.length + 1}`,
        title,
        description: openLoopDescription,
        due_at: openLoopDueAt || null,
        priority: openLoopPriority,
        status: "open",
        memory_id: selectedReview?.id ?? null,
        project_id: selectedProjectId || null,
        domain: selectedReview ? asDomain(selectedReview.domain) : defaultDomain,
        sensitivity: selectedReview ? asSensitivity(selectedReview.sensitivity) : defaultSensitivity,
      };
      updateFixtureWorkspace(
        (previous) => {
          const view = { ...previous, openLoops: [nextLoop, ...previous.openLoops] };
          return { ...view, summary: createSummary(view) };
        },
        "Demo open loop created.",
      );
      setSelectedOpenLoopId(nextLoop.id);
      return;
    }

    await runLiveAction(
      "Creating open loop...",
      async () => {
        await createVNextOpenLoop(apiBaseUrl, {
          user_id: userId,
          title,
          description: openLoopDescription.trim() || undefined,
          due_at: openLoopDueAt.trim() || undefined,
          priority: openLoopPriority,
          memory_id: selectedReview?.id,
          project_id: selectedProjectId || undefined,
          source_id: textValue(asRecord(selectedReview?.metadata_json).source_id) || undefined,
          domain: selectedReview ? asDomain(selectedReview.domain) : defaultDomain,
          sensitivity: selectedReview ? asSensitivity(selectedReview.sensitivity) : defaultSensitivity,
        });
      },
      "Open loop created from live workspace.",
    );
  }

  async function handleSourceAction(action: "review" | "update" | "assign_project" | "archive") {
    if (!selectedSource) {
      return;
    }
    if (action === "assign_project" && !sourceProjectDraft) {
      setStatusTone("danger");
      setStatusText("Choose a project before assigning the source.");
      return;
    }

    if (!liveModeReady || !apiBaseUrl || !userId) {
      updateFixtureWorkspace(
        (previous) => {
          const now = new Date().toISOString();
          if (action === "archive") {
            const view = {
              ...previous,
              sources: previous.sources.filter((source) => source.id !== selectedSource.id),
              traceability: {
                ...previous.traceability,
                items: previous.traceability.items.filter((trace) => trace.summary.source_id !== selectedSource.id),
                count: previous.traceability.items.filter((trace) => trace.summary.source_id !== selectedSource.id).length,
                order: previous.traceability.order.filter((traceId) => traceId !== `source:${selectedSource.id}`),
              },
            };
            return { ...view, summary: createSummary(view) };
          }
          const nextSources = previous.sources.map((source) =>
            source.id === selectedSource.id
              ? {
                  ...source,
                  title: sourceTitleDraft,
                  domain: sourceDomainDraft,
                  sensitivity: sourceSensitivityDraft,
                  metadata_json: {
                    ...asRecord(source.metadata_json),
                    review_status: action === "review" ? "reviewed" : "updated",
                    reviewed_at: now,
                    review_note: sourceReviewNote,
                    project_id: action === "assign_project" ? sourceProjectDraft : asRecord(source.metadata_json).project_id,
                    updated_from: "vnext_workspace",
                  },
                }
              : source,
          );
          const traceability = {
            ...previous.traceability,
            items: previous.traceability.items.map((trace) =>
              trace.summary.source_id === selectedSource.id
                ? {
                    ...trace,
                    source: nextSources.find((source) => source.id === selectedSource.id) ?? trace.source,
                  }
                : trace,
            ),
          };
          const view = { ...previous, sources: nextSources, traceability };
          return { ...view, summary: createSummary(view) };
        },
        `Demo source action applied: ${action}.`,
      );
      return;
    }

    await runLiveAction(
      `Applying source action: ${action}...`,
      async () => {
        await reviewVNextSource(apiBaseUrl, selectedSource.id, {
          user_id: userId,
          action,
          title: action === "archive" ? undefined : sourceTitleDraft,
          domain: action === "archive" ? undefined : sourceDomainDraft,
          sensitivity: action === "archive" ? undefined : sourceSensitivityDraft,
          project_id: action === "assign_project" ? sourceProjectDraft : undefined,
          review_note: sourceReviewNote.trim() || undefined,
        });
      },
      `Source action applied: ${action}.`,
    );
  }

  async function handleCreateOpenLoopFromSource() {
    if (!selectedSource) {
      return;
    }
    const title = openLoopTitle.trim() || `Review ${sourceTitleDraft || selectedSource.title || selectedSource.source_type}`;
    if (!liveModeReady || !apiBaseUrl || !userId) {
      const nextLoop: VNextOpenLoopRecord = {
        id: `loop-source-demo-${workspace.openLoops.length + 1}`,
        title,
        description: sourceReviewNote,
        due_at: openLoopDueAt || null,
        priority: openLoopPriority,
        status: "open",
        source_id: selectedSource.id,
        project_id: sourceProjectDraft || null,
        domain: sourceDomainDraft,
        sensitivity: sourceSensitivityDraft,
      };
      updateFixtureWorkspace(
        (previous) => {
          const traceability = {
            ...previous.traceability,
            items: previous.traceability.items.map((trace) =>
              trace.summary.source_id === selectedSource.id
                ? {
                    ...trace,
                    open_loops: [nextLoop, ...trace.open_loops],
                    summary: {
                      ...trace.summary,
                      open_loop_count: trace.summary.open_loop_count + 1,
                    },
                  }
                : trace,
            ),
          };
          const view = { ...previous, openLoops: [nextLoop, ...previous.openLoops], traceability };
          return { ...view, summary: createSummary(view) };
        },
        "Demo source-backed open loop created.",
      );
      setSelectedOpenLoopId(nextLoop.id);
      return;
    }

    await runLiveAction(
      "Creating source-backed open loop...",
      async () => {
        await createVNextOpenLoop(apiBaseUrl, {
          user_id: userId,
          title,
          description: sourceReviewNote.trim() || undefined,
          due_at: openLoopDueAt.trim() || undefined,
          priority: openLoopPriority,
          project_id: sourceProjectDraft || undefined,
          source_id: selectedSource.id,
          domain: sourceDomainDraft,
          sensitivity: sourceSensitivityDraft,
        });
      },
      "Source-backed open loop created.",
    );
  }

  async function handleOpenLoopAction(action: "close" | "snooze" | "edit" | "reopen") {
    const selectedLoop = workspace.openLoops.find((loop) => loop.id === selectedOpenLoopId);
    if (!selectedLoop) {
      return;
    }

    if (!liveModeReady || !apiBaseUrl || !userId) {
      updateFixtureWorkspace(
        (previous) => {
          const nextLoops = previous.openLoops.map((loop) =>
            loop.id === selectedLoop.id
              ? {
                  ...loop,
                  status: action === "close" ? "resolved" : action === "reopen" ? "open" : loop.status,
                  title: action === "edit" ? openLoopTitle : loop.title,
                  description: action === "edit" ? openLoopDescription : loop.description,
                  due_at: action === "snooze" || action === "edit" ? openLoopDueAt || loop.due_at : loop.due_at,
                  priority: action === "edit" ? openLoopPriority : loop.priority,
                }
              : loop,
          );
          const view = { ...previous, openLoops: nextLoops };
          return { ...view, summary: createSummary(view) };
        },
        `Demo open-loop action applied: ${action}.`,
      );
      return;
    }

    await runLiveAction(
      `Applying open-loop action: ${action}...`,
      async () => {
        await reviewVNextOpenLoop(apiBaseUrl, selectedLoop.id, {
          user_id: userId,
          action,
          title: action === "edit" ? openLoopTitle : undefined,
          description: action === "edit" ? openLoopDescription : undefined,
          due_at: action === "snooze" || action === "edit" ? openLoopDueAt || undefined : undefined,
          priority: action === "edit" ? openLoopPriority : undefined,
          resolution_note: action === "close" ? "Closed from live /vnext workspace." : undefined,
        });
      },
      `Open-loop action applied: ${action}.`,
    );
  }

  async function handleGenerateArtifact(kind: "daily" | "weekly" | "project") {
    if (!liveModeReady || !apiBaseUrl || !userId) {
      const artifactType =
        kind === "daily" ? "daily_brief" : kind === "weekly" ? "weekly_synthesis" : "project_update";
      const nextArtifact: VNextArtifactRecord = {
        id: `artifact-demo-${workspace.artifacts.length + 1}`,
        artifact_type: artifactType,
        title:
          kind === "daily"
            ? "Daily Brief - Demo"
            : kind === "weekly"
              ? "Weekly Synthesis - Demo"
              : "Project Update Candidate - Demo",
        content_markdown:
          generationMode === "model_backed"
            ? `# ${kind} demo artifact\n\n## Facts\n- Demo source evidence is selected.\n\n## Inferences\n- The workspace has enough context to synthesize a reviewable artifact.\n\n## Recommendations\n- Keep the artifact in review.\n\n## Uncertainties\n- Live source coverage may differ from fixture data.\n\n## Source References\n- source:demo\n\n## Contradictions Considered\n- No explicit contradiction candidates were supplied.\n\n## Open Questions\n- Which source should be reviewed next?`
            : `# ${kind} demo artifact\n\nGenerated from fixture workspace state.`,
        status: "needs_review",
        domain: defaultDomain,
        sensitivity: defaultSensitivity,
        generated_by: "vnext_demo_workspace",
        model_info_json:
          generationMode === "model_backed"
            ? {
                provider: "deterministic_local",
                model: "alice-vnext-grounded-synthesizer-v1",
                prompt_hash: "sha256:demo-prompt",
                input_context_hash: "sha256:demo-context",
                policy_mode: "local_only_default",
              }
            : null,
        metadata_json: { workflow: artifactType, project_id: selectedProjectId, generation_mode: generationMode },
      };
      updateFixtureWorkspace(
        (previous) => {
          const view = { ...previous, artifacts: [nextArtifact, ...previous.artifacts] };
          return { ...view, summary: createSummary(view) };
        },
        `Demo ${kind} artifact generated.`,
      );
      return;
    }

    await runLiveAction(
      `Generating ${kind} artifact...`,
      async () => {
        const payload = {
          user_id: userId,
          scope: { domains: [defaultDomain], project_id: selectedProjectId || undefined },
          options: {
            sensitivity_allowed: ["public", "internal", "private", "unknown"],
            discover_open_loops: true,
            create_candidate_memories: true,
            generation_mode: generationMode,
            model_route_mode: "local_only",
            model_provider: "deterministic_local",
          },
        };
        if (kind === "daily") {
          await generateVNextDailyBrief(apiBaseUrl, payload);
        } else if (kind === "weekly") {
          await generateVNextWeeklySynthesis(apiBaseUrl, payload);
        } else {
          await generateVNextProjectUpdate(apiBaseUrl, {
            user_id: userId,
            scope: { project_id: selectedProjectId || undefined, domains: [defaultDomain] },
            options: {
              sensitivity_allowed: ["public", "internal", "private", "unknown"],
              generation_mode: generationMode,
              model_route_mode: "local_only",
              model_provider: "deterministic_local",
            },
          });
        }
      },
      `${kind} artifact generated and held for review.`,
    );
  }

  async function handleSchedulerAction(
    workflow: VNextSchedulerStatus["workflows"][number],
    action: "enable" | "disable" | "pause" | "resume" | "run_now" | "update_schedule",
  ) {
    const draft = schedulerDrafts[workflow.workflow_type] ?? {
      timeOfDay: scheduleValue(workflow, "time_of_day", workflow.workflow_type === "weekly_synthesis" ? "09:00" : "08:00"),
      dayOfWeek: scheduleValue(workflow, "day_of_week", "monday"),
      timezone: workflow.timezone || "UTC",
    };
    const scheduleJson =
      workflow.workflow_type === "daily_brief"
        ? { kind: "daily", time_of_day: draft.timeOfDay, days_of_week: ["monday", "tuesday", "wednesday", "thursday", "friday"] }
        : workflow.workflow_type === "weekly_synthesis"
          ? { kind: "weekly", day_of_week: draft.dayOfWeek, time_of_day: draft.timeOfDay }
          : { kind: "manual" };

    if (!liveModeReady || !apiBaseUrl || !userId) {
      updateFixtureWorkspace(
        (previous) => {
          const now = new Date().toISOString();
          const runId = `scheduler-run-demo-${previous.scheduler.recent_runs.length + 1}`;
          const nextArtifact: VNextArtifactRecord | null =
            action === "run_now"
              ? {
                  id: `artifact-scheduler-demo-${previous.artifacts.length + 1}`,
                  artifact_type: workflow.workflow_type,
                  title: `${workflow.workflow_type.replace(/_/g, " ")} - scheduler demo`,
                  content_markdown: `# ${workflow.workflow_type}\n\nGenerated by the governed scheduler demo path.`,
                  status: "needs_review",
                  domain: defaultDomain,
                  sensitivity: defaultSensitivity,
                  generated_by: "scheduler",
                  metadata_json: {
                    workflow: workflow.workflow_type,
                    workflow_type: workflow.workflow_type,
                    scheduler_run_id: runId,
                    trace_id: `trace-${runId}`,
                    generated_by: "scheduler",
                    source_refs: [],
                    review_status: "needs_review",
                    generation_mode: generationMode,
                  },
                  model_info_json:
                    generationMode === "model_backed"
                      ? {
                          provider: "deterministic_local",
                          model: "alice-vnext-grounded-synthesizer-v1",
                          prompt_hash: "sha256:scheduler-demo-prompt",
                          input_context_hash: "sha256:scheduler-demo-context",
                          policy_mode: "local_only_default",
                        }
                      : null,
                }
              : null;
          const nextRun =
            action === "run_now"
              ? {
                  id: runId,
                  workflow_type: workflow.workflow_type,
                  status: "succeeded",
                  triggered_by: "user",
                  trace_id: `trace-${runId}`,
                  started_at: now,
                  finished_at: now,
                  artifact_id: nextArtifact?.id ?? null,
                  metadata_json: { demo: true },
                }
              : null;
          const workflows = previous.scheduler.workflows.map((item) =>
            item.id === workflow.id
              ? {
                  ...item,
                  enabled: action === "enable" ? true : action === "disable" ? false : item.enabled,
                  paused: action === "pause" ? true : action === "resume" ? false : item.paused,
                  schedule_json: action === "update_schedule" ? scheduleJson : item.schedule_json,
                  timezone: action === "update_schedule" ? draft.timezone : item.timezone,
                  last_run_id: nextRun?.id ?? item.last_run_id,
                  last_run_at: nextRun?.finished_at ?? item.last_run_at,
                  last_result: nextRun ? "succeeded" : item.last_result,
                  last_error: nextRun ? null : item.last_error,
                }
              : item,
          );
          const scheduler = {
            ...previous.scheduler,
            workflows,
            recent_runs: nextRun ? [nextRun, ...previous.scheduler.recent_runs] : previous.scheduler.recent_runs,
            enabled_count: workflows.filter((item) => item.enabled).length,
            paused_count: workflows.filter((item) => item.paused).length,
          };
          const event: VNextEventRecord = {
            id: `scheduler-event-demo-${previous.recentEvents.length + 1}`,
            event_type: action === "run_now" ? "scheduler.run_succeeded" : `scheduler.workflow_${action}`,
            actor_type: "user",
            target_type: "scheduler_workflow",
            target_id: workflow.id,
            occurred_at: now,
            payload_json: { workflow_type: workflow.workflow_type },
          };
          const view = {
            ...previous,
            scheduler,
            artifacts: nextArtifact ? [nextArtifact, ...previous.artifacts] : previous.artifacts,
            recentEvents: [event, ...previous.recentEvents],
          };
          return { ...view, summary: createSummary(view) };
        },
        `Demo scheduler action applied: ${action}.`,
      );
      return;
    }

    await runLiveAction(
      `Applying scheduler action: ${action}...`,
      async () => {
        if (action === "run_now") {
          await runVNextSchedulerWorkflowNow(apiBaseUrl, workflow.workflow_type, {
            user_id: userId,
            scope: { domains: [defaultDomain] },
            options: {
              sensitivity_allowed: ["public", "internal", "private", "unknown"],
              generation_mode: generationMode,
              model_route_mode: "local_only",
              model_provider: "deterministic_local",
            },
          });
          return;
        }
        await patchVNextSchedulerWorkflow(apiBaseUrl, workflow.workflow_type, {
          user_id: userId,
          enabled: action === "enable" ? true : action === "disable" ? false : undefined,
          paused: action === "pause" ? true : action === "resume" ? false : undefined,
          schedule_json: action === "update_schedule" ? scheduleJson : undefined,
          timezone: action === "update_schedule" ? draft.timezone : undefined,
          model_options:
            action === "update_schedule" || action === "enable"
              ? {
                  generation_mode: generationMode,
                  model_route_mode: "local_only",
                  model_provider: "deterministic_local",
                }
              : undefined,
        });
      },
      `Scheduler action applied: ${action}.`,
    );
  }

  async function handleSchedulerRunDue() {
    if (!liveModeReady || !apiBaseUrl || !userId) {
      updateFixtureWorkspace(
        (previous) => {
          const now = new Date().toISOString();
          const dueWorkflows = previous.scheduler.workflows.filter((workflow) => workflow.enabled && !workflow.paused);
          const runs = dueWorkflows.map((workflow, index) => ({
            id: `scheduler-due-demo-${previous.scheduler.recent_runs.length + index + 1}`,
            workflow_type: workflow.workflow_type,
            status: "succeeded",
            triggered_by: "scheduler",
            trace_id: `trace-due-demo-${index + 1}`,
            started_at: now,
            finished_at: now,
            artifact_id: `artifact-due-demo-${index + 1}`,
            metadata_json: { demo: true },
          }));
          const workflows = previous.scheduler.workflows.map((workflow) =>
            runs.some((run) => run.workflow_type === workflow.workflow_type)
              ? { ...workflow, last_run_at: now, last_result: "succeeded", next_run_at: null }
              : workflow,
          );
          const event: VNextEventRecord = {
            id: `scheduler-due-event-demo-${previous.recentEvents.length + 1}`,
            event_type: "scheduler.due_scan",
            actor_type: "scheduler",
            occurred_at: now,
            payload_json: { checked_at: now, due_count: runs.length },
          };
          const view = {
            ...previous,
            scheduler: {
              ...previous.scheduler,
              workflows,
              recent_runs: [...runs, ...previous.scheduler.recent_runs],
              last_due_scan: event,
              daemon: { ...previous.scheduler.daemon, configured: true, running: false, last_due_scan_at: now, last_due_count: runs.length },
            },
            recentEvents: [event, ...previous.recentEvents],
          };
          return { ...view, summary: createSummary(view) };
        },
        "Demo due scan applied.",
      );
      return;
    }

    await runLiveAction(
      "Running due scheduler workflows...",
      async () => {
        await runVNextSchedulerDue(apiBaseUrl, { user_id: userId, limit: 10 });
      },
      "Due scheduler workflows completed.",
    );
  }

  async function handleArtifactAction(artifact: VNextArtifactRecord, action: "review" | "accept" | "reject" | "promote" | "archive") {
    if (!liveModeReady || !apiBaseUrl || !userId) {
      const statusMap = {
        review: "reviewed",
        accept: "accepted",
        reject: "rejected",
        promote: "promoted_to_memory",
        archive: "archived",
      };
      updateFixtureWorkspace(
        (previous) => {
          const nextArtifacts = previous.artifacts.map((item) =>
            item.id === artifact.id ? { ...item, status: statusMap[action] } : item,
          );
          const view = { ...previous, artifacts: nextArtifacts };
          return { ...view, summary: createSummary(view) };
        },
        `Demo artifact action applied: ${action}.`,
      );
      return;
    }

    await runLiveAction(
      `Applying artifact action: ${action}...`,
      async () => {
        await reviewVNextArtifact(apiBaseUrl, artifact.id, { user_id: userId, action });
      },
      `Artifact action applied: ${action}.`,
    );
  }

  async function handleQualityRating(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const artifactId = qualityArtifactId || workspace.artifacts[0]?.id || "";
    if (!artifactId) {
      setStatusTone("danger");
      setStatusText("Quality rating needs a generated artifact.");
      return;
    }
    if (!liveModeReady || !apiBaseUrl || !userId) {
      const nextEval: VNextArtifactQualityEvalRecord = {
        id: `quality-demo-${workspace.qualityEvals.length + 1}`,
        artifact_id: artifactId,
        reviewer_id: "demo-reviewer",
        ...qualityScores,
        verbosity: qualityVerbosity,
        comments: qualityComments || null,
        created_at: new Date().toISOString(),
      };
      updateFixtureWorkspace(
        (previous) => {
          const view = { ...previous, qualityEvals: [nextEval, ...previous.qualityEvals] };
          return { ...view, summary: createSummary(view) };
        },
        "Demo artifact quality rating saved.",
      );
      return;
    }
    await runLiveAction(
      "Saving artifact quality rating...",
      async () => {
        await rateVNextArtifactQuality(apiBaseUrl, artifactId, {
          user_id: userId,
          ...qualityScores,
          verbosity: qualityVerbosity,
          comments: qualityComments || undefined,
        });
      },
      "Artifact quality rating saved.",
    );
  }

  async function handleCreateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newProjectName.trim();
    if (!name) {
      setStatusTone("danger");
      setStatusText("Project creation needs a name.");
      return;
    }

    if (!liveModeReady || !apiBaseUrl || !userId) {
      const nextProject: VNextProjectRecord = {
        id: `project-demo-${workspace.projects.length + 1}`,
        name,
        slug: name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "project",
        status: "active",
        current_state: newProjectState,
        domain: defaultDomain,
        sensitivity: defaultSensitivity,
      };
      updateFixtureWorkspace(
        (previous) => {
          const nextDashboards = [
            {
              project: nextProject,
              state: nextProject.current_state ?? null,
              memories: [],
              open_loops: [],
              artifacts: [],
              counts: { memories: 0, open_loops: 0, artifacts: 0 },
            },
            ...previous.projectDashboards,
          ];
          const view = {
            ...previous,
            projects: [nextProject, ...previous.projects],
            projectDashboards: nextDashboards,
          };
          return { ...view, summary: createSummary(view) };
        },
        "Demo project created.",
      );
      setSelectedProjectId(nextProject.id);
      return;
    }

    await runLiveAction(
      "Creating project...",
      async () => {
        await createVNextProject(apiBaseUrl, {
          user_id: userId,
          name,
          current_state: newProjectState.trim() || undefined,
          domain: defaultDomain,
          sensitivity: defaultSensitivity,
        });
      },
      "Project created and dashboard refreshed.",
    );
  }

  async function handleSaveCharter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!charterText.trim()) {
      setStatusTone("danger");
      setStatusText("Brain Charter text is required.");
      return;
    }
    if (!liveModeReady || !apiBaseUrl || !userId) {
      const brainCharter: VNextBrainCharterRecord = {
        id: workspace.brainCharter?.id ?? "brain-charter-demo",
        content_markdown: charterText,
        sensitivity: charterSensitivity,
      };
      updateFixtureWorkspace(
        (previous) => ({ ...previous, brainCharter }),
        "Demo Brain Charter settings saved.",
      );
      return;
    }

    await runLiveAction(
      "Saving Brain Charter...",
      async () => {
        await upsertVNextBrainCharter(apiBaseUrl, {
          user_id: userId,
          content_markdown: charterText,
          sensitivity: charterSensitivity,
          life_domains_json: {
            default_domain: defaultDomain,
            default_sensitivity: defaultSensitivity,
          },
          autonomous_rules_json: ["Generated artifacts require explicit review before promotion."],
          quality_standard_json: ["Show provenance for answers and generated artifacts."],
        });
      },
      "Brain Charter settings saved.",
    );
  }

  function updateConnectorFixture(connectorId: string, message: string) {
    updateFixtureWorkspace((previous) => {
      const existing = connectorHealth(previous, connectorId);
      const nextItem: VNextConnectorHealthRecord = {
        connector_name: connectorId,
        display_name: INITIAL_CONNECTORS.find((item) => item.id === connectorId)?.name ?? connectorId,
        enabled: connectorEnabled,
        configured: true,
        default_domain: connectorDomain,
        default_sensitivity: connectorSensitivity,
        sync_mode: connectorId === "telegram" ? "polling" : connectorId === "local_folder" ? "watch" : "on_demand",
        poll_interval_seconds: connectorId === "telegram" ? 60 : connectorId === "local_folder" ? 30 : null,
        validation_errors: [],
        secret_configured: Boolean(connectorSecretRef.trim()),
        last_sync_at: existing?.last_sync_at ?? null,
        last_success_at: existing?.last_success_at ?? null,
        last_failure_at: existing?.last_failure_at ?? null,
        last_error: existing?.last_error ?? null,
        last_captured_item: existing?.last_captured_item ?? null,
        items_seen: existing?.items_seen ?? 0,
        items_captured: existing?.items_captured ?? 0,
        items_deduped: existing?.items_deduped ?? 0,
        items_failed: existing?.items_failed ?? 0,
        cursor_state: existing?.cursor_state ?? null,
        average_processing_time: existing?.average_processing_time ?? null,
      };
      const items = [
        nextItem,
        ...previous.connectorHealth.items.filter((item) => item.connector_name !== connectorId),
      ];
      const connectorHealthPayload = {
        items,
        count: items.length,
        order: items.map((item) => item.connector_name),
      };
      return {
        ...previous,
        connectorHealth: connectorHealthPayload,
        dogfooding: {
          ...previous.dogfooding,
          connector_health: connectorHealthPayload,
        },
      };
    }, message);
  }

  async function handleSaveConnectorSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const selectedConnector = INITIAL_CONNECTORS.find((connector) => connector.id === selectedConnectorId) ?? INITIAL_CONNECTORS[0];
    const configJson: JsonObject =
      selectedConnector.id === "telegram"
        ? {
            allowed_chat_ids: telegramAllowedChats
              .split(/[,\n]/)
              .map((value) => value.trim())
              .filter(Boolean),
          }
        : selectedConnector.id === "local_folder"
          ? {
              paths: localFolderPath.trim() ? [localFolderPath.trim()] : [],
              recursive: true,
              extensions: localFolderExtensions
                .split(",")
                .map((value) => value.trim())
                .filter(Boolean),
              ignore_patterns: localFolderIgnores
                .split(",")
                .map((value) => value.trim())
                .filter(Boolean),
            }
          : {};
    if (!liveModeReady || !apiBaseUrl || !userId) {
      updateConnectorFixture(selectedConnector.id, "Demo connector settings saved.");
      return;
    }
    await runLiveAction(
      "Saving connector settings...",
      async () => {
        await updateVNextConnectorConfig(apiBaseUrl, selectedConnector.id, {
          user_id: userId,
          enabled: connectorEnabled,
          default_domain: connectorDomain,
          default_sensitivity: connectorSensitivity,
          secret_ref: connectorSecretRef.trim() || null,
          sync_mode: selectedConnector.id === "telegram" ? "polling" : selectedConnector.id === "local_folder" ? "watch" : "on_demand",
          poll_interval_seconds: selectedConnector.id === "telegram" ? 60 : selectedConnector.id === "local_folder" ? 30 : null,
          config_json: configJson,
        });
      },
      "Connector settings saved.",
    );
  }

  async function handleRunConnectorSync() {
    const selectedConnector = INITIAL_CONNECTORS.find((connector) => connector.id === selectedConnectorId) ?? INITIAL_CONNECTORS[0];
    if (!liveModeReady || !apiBaseUrl || !userId) {
      updateConnectorFixture(selectedConnector.id, "Demo connector sync completed.");
      return;
    }
    await runLiveAction(
      "Running connector sync...",
      async () => {
        if (selectedConnector.id === "telegram") {
          await syncVNextTelegramConnector(apiBaseUrl, {
            user_id: userId,
            allowed_chat_ids: telegramAllowedChats
              .split(/[,\n]/)
              .map((value) => value.trim())
              .filter(Boolean),
            default_domain: connectorDomain,
            default_sensitivity: connectorSensitivity,
          });
        } else if (selectedConnector.id === "local_folder") {
          await syncVNextLocalFolderConnector(apiBaseUrl, {
            user_id: userId,
            paths: localFolderPath.trim() ? [localFolderPath.trim()] : [],
            recursive: true,
            extensions: localFolderExtensions
              .split(",")
              .map((value) => value.trim())
              .filter(Boolean),
            ignore_patterns: localFolderIgnores
              .split(",")
              .map((value) => value.trim())
              .filter(Boolean),
            default_domain: connectorDomain,
            default_sensitivity: connectorSensitivity,
          });
        }
      },
      "Connector sync completed.",
    );
  }

  async function handleTestBrowserClip() {
    if (!liveModeReady || !apiBaseUrl || !userId) {
      updateConnectorFixture("browser_clipper", "Demo browser clip captured.");
      return;
    }
    await runLiveAction(
      "Capturing browser clip...",
      async () => {
        await captureVNextBrowserClip(apiBaseUrl, {
          user_id: userId,
          url: browserClipUrl,
          title: "vNext connector test clip",
          selected_text: browserClipSelection,
          domain: connectorDomain,
          sensitivity: connectorSensitivity,
        });
      },
      "Browser clip captured.",
    );
  }

  async function handleRunDoctor(fixSafe: boolean) {
    if (fixSafe && typeof window !== "undefined" && !window.confirm("Run vNext doctor --fix-safe?")) {
      return;
    }
    if (!liveModeReady || !apiBaseUrl || !userId) {
      updateFixtureWorkspace(
        (previous) => ({
          ...previous,
          doctor: {
            ...previous.doctor,
            status: "pass",
            fix_safe_applied: fixSafe,
            checks: previous.doctor.checks.length ? previous.doctor.checks : FIXTURE_DOCTOR.checks,
            recommended_fixes: [],
          },
        }),
        fixSafe ? "Demo doctor safe fix completed." : "Demo doctor check completed.",
      );
      return;
    }
    await runLiveAction(
      fixSafe ? "Running doctor safe fix..." : "Running doctor checks...",
      async () => {
        await runVNextDoctor(apiBaseUrl, { user_id: userId, fix_safe: fixSafe, ci: true });
      },
      fixSafe ? "Doctor safe fix completed." : "Doctor checks completed.",
    );
  }

  const selectedLoop = workspace.openLoops.find((loop) => loop.id === selectedOpenLoopId) ?? workspace.openLoops[0] ?? null;
  const selectedConnector =
    INITIAL_CONNECTORS.find((connector) => connector.id === selectedConnectorId) ?? INITIAL_CONNECTORS[0];
  const browserClipperEndpoint = `${apiBaseUrl || "http://127.0.0.1:8000"}/v0/vnext/connectors/browser-clipper/capture`;
  const activeSourceLabel = dataSource === "live" ? "Live API" : "Demo fixture";
  const status = pendingAction ? "loading" : statusTone === "success" ? "success" : statusTone === "danger" ? "error" : isRefreshing ? "loading" : dataSource;

  return (
    <div className="page-stack">
      <VNextSurfaceNavigation />

      <div
        className="composer-status"
        role={statusTone === "danger" ? "alert" : "status"}
        aria-live={statusTone === "danger" ? "assertive" : "polite"}
        aria-atomic="true"
        aria-busy={Boolean(pendingAction || isRefreshing)}
      >
        <StatusBadge status={status} label={pendingAction ? "Working" : activeSourceLabel} />
        <span>{statusText}</span>
        <StatusBadge status="blocked" label="No auto-promotion" />
      </div>

      {liveModeReady ? (
        <SectionCard
          eyebrow="Local session authentication"
          title="Operator API key"
          description="After any agent key is provisioned, the full review console requires an unbound admin_agent key entered for this browser session. trusted_local_agent does not grant all human/admin review actions."
        >
          <form className="detail-stack" onSubmit={handleOperatorAgentApiKeySubmit}>
            <div className="form-field">
              <label htmlFor="vnext-operator-agent-api-key">Unbound admin_agent API key</label>
              <input
                id="vnext-operator-agent-api-key"
                type="password"
                autoComplete="off"
                spellCheck={false}
                value={operatorAgentApiKey}
                onChange={(event) => handleOperatorAgentApiKeyChange(event.target.value)}
                aria-describedby="vnext-operator-agent-api-key-help"
              />
            </div>
            <div className="button-row">
              <button
                type="submit"
                className="button button--primary"
                disabled={!operatorAgentApiKey.trim() || isRefreshing || Boolean(pendingAction)}
              >
                Use key for this session
              </button>
              <button
                type="button"
                className="button button--secondary"
                disabled={!operatorAgentApiKey && !operatorAgentApiKeyActive}
                onClick={handleClearOperatorAgentApiKey}
              >
                Clear session key
              </button>
            </div>
          </form>
          <div className="status-row">
            <StatusBadge
              status={operatorAgentApiKeyActive ? "active" : "needs_review"}
              label={operatorAgentApiKeyActive ? "Key held in memory" : "No session key"}
            />
            <p id="vnext-operator-agent-api-key-help" className="muted-copy">
              The key is held only in this mounted browser session, cleared on edit, clear, or
              unmount, and forwarded only to loopback <code>/v0/vnext</code> requests. It is never
              read from environment variables, local storage, URLs, logs, or error output.
            </p>
          </div>
        </SectionCard>
      ) : null}

      <VNextHomeMetrics workspace={workspace} />

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Home"
          title="Recent activity"
          description="Live mode reads the append-only vNext event log so the dashboard reflects real workspace actions."
        >
          {isRefreshing ? (
            <div className="loading-placeholder loading-placeholder--line" />
          ) : workspace.recentEvents.length ? (
            <div className="timeline-list">
              {workspace.recentEvents.slice(0, 5).map((event) => (
                <article key={event.id} className="timeline-item">
                  <div className="timeline-item__topline">
                    <span className="list-row__eyebrow mono">{event.occurred_at}</span>
                    <h3 className="list-row__title">{eventTitle(event)}</h3>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="No vNext activity yet" description="Capture a note to create the first live event-log entry." />
          )}
        </SectionCard>

        <SectionCard
          eyebrow="Dogfooding"
          title="Capture health loop"
          description="Shows whether Alice is being fed, reviewed, rated, and used by agents."
        >
          <dl className="key-value-grid key-value-grid--compact">
            <div>
              <dt>Readiness</dt>
              <dd>{workspace.dogfooding.dogfood_readiness?.status ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Captures today</dt>
              <dd>{workspace.dogfooding.captures_today}</dd>
            </div>
            <div>
              <dt>This week</dt>
              <dd>{workspace.dogfooding.captures_this_week}</dd>
            </div>
            <div>
              <dt>Quality avg</dt>
              <dd>{workspace.dogfooding.artifact_quality_average ?? "n/a"}</dd>
            </div>
            <div>
              <dt>Useful insight</dt>
              <dd>{workspace.dogfooding.insight_feedback.useful_yes}/{workspace.dogfooding.insight_feedback.count}</dd>
            </div>
            <div>
              <dt>Agent proposals</dt>
              <dd>{workspace.dogfooding.agent_memory_proposals}</dd>
            </div>
            <div>
              <dt>Connector failures</dt>
              <dd>{workspace.dogfooding.connector_failures}</dd>
            </div>
            <div>
              <dt>Review rate</dt>
              <dd>{workspace.dogfooding.candidate_memory_review_rate ?? 0}</dd>
            </div>
          </dl>
          <p className="section-note">{workspace.dogfooding.dogfood_readiness?.reason ?? "No dogfooding readiness signal yet."}</p>
          <div className="cluster">
            {workspace.dogfooding.captures_by_connector.map((item) => (
              <span key={item.connector_name} className="meta-pill">
                {item.connector_name}: {item.count}
              </span>
            ))}
            {(workspace.dogfooding.top_failure_causes ?? []).map((item) => (
              <span key={item.cause} className="meta-pill">
                Failure: {item.cause} ({item.count})
              </span>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Settings"
          title="Privacy defaults"
          description="Capture, retrieval, generated artifacts, and review actions keep domain and sensitivity labels visible."
        >
          <div id="vnext-settings" className="detail-stack">
            <div className="form-field-group form-field-group--two-up">
              <div className="form-field">
                <label htmlFor="vnext-default-domain">Default domain</label>
                <select
                  id="vnext-default-domain"
                  value={defaultDomain}
                  onChange={(event) => setDefaultDomain(event.target.value as Domain)}
                >
                  {VNEXT_DOMAIN_OPTIONS.map((domain) => (
                    <option key={domain.value} value={domain.value}>
                      {domain.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="vnext-default-sensitivity">Default sensitivity</label>
                <select
                  id="vnext-default-sensitivity"
                  value={defaultSensitivity}
                  onChange={(event) => setDefaultSensitivity(event.target.value as Sensitivity)}
                >
                  {VNEXT_SENSITIVITY_OPTIONS.map((sensitivity) => (
                    <option key={sensitivity.value} value={sensitivity.value}>
                      {sensitivity.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="cluster">
              <StatusBadge status="active" label="Local-first" />
              <StatusBadge status="requires_review" label="Generated output held" />
              <span className="meta-pill">Domain: {domainLabel(defaultDomain)}</span>
              <span className="meta-pill">Sensitivity: {sensitivityLabel(defaultSensitivity)}</span>
            </div>
            <div className="form-field">
              <label htmlFor="vnext-generation-mode">Generation mode</label>
              <select
                id="vnext-generation-mode"
                value={generationMode}
                onChange={(event) => setGenerationMode(event.target.value as "deterministic" | "model_backed")}
              >
                <option value="deterministic">Deterministic</option>
                <option value="model_backed">Model-backed local</option>
              </select>
            </div>
          </div>
        </SectionCard>
      </div>

      <div id="vnext-inbox" className="vnext-review-layout">
        <SectionCard
          eyebrow="Inbox"
          title="Source capture"
          description="Adding a note calls the vNext source API in live mode, which creates source chunks, provenance, candidate memories, and event-log entries."
        >
          <form className="detail-stack" onSubmit={handleCapture}>
            <div className="form-field">
              <label htmlFor="vnext-capture-title">Source title</label>
              <input
                id="vnext-capture-title"
                value={captureTitle}
                onChange={(event) => setCaptureTitle(event.target.value)}
              />
            </div>
            <div className="form-field">
              <label htmlFor="vnext-capture-text">Note or source text</label>
              <textarea
                id="vnext-capture-text"
                value={captureText}
                onChange={(event) => setCaptureText(event.target.value)}
              />
              <p className="field-hint">{captureText.length}/200000</p>
            </div>
            <button type="submit" className="button" disabled={Boolean(pendingAction)}>
              Add note/source
            </button>
          </form>

          <div className="list-rows">
            {workspace.sources.length ? (
              workspace.sources.slice(0, 5).map((source) => (
                <button
                  key={source.id}
                  type="button"
                  className={`list-row vnext-review-button${selectedSource?.id === source.id ? " is-selected" : ""}`}
                  onClick={() => setSelectedSourceId(source.id)}
                >
                  <span className="list-row__topline">
                    <span className="detail-stack">
                      <span className="list-row__eyebrow mono">{source.source_type}</span>
                      <span className="list-row__title">{source.title || source.id}</span>
                    </span>
                    <StatusBadge status={source.sensitivity ?? "unknown"} />
                  </span>
                  <span>{sourceText(source).slice(0, 220)}</span>
                  <span className="list-row__meta">
                    <span className="meta-pill">Domain: {domainLabel(asDomain(source.domain))}</span>
                    <span className="meta-pill">Review: {textValue(asRecord(source.metadata_json).review_status) || "unreviewed"}</span>
                    <span className="meta-pill">Captured: {source.captured_at}</span>
                  </span>
                </button>
              ))
            ) : (
              <EmptyState title="Inbox is empty" description="Capture a note to create a live source and candidate memory." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Inbox"
          title="Source detail and review"
          description="Selected source evidence can be reviewed, relabeled, assigned to a project, archived, or turned into an open loop without promoting memory."
        >
          <div className="detail-stack">
            {selectedSource ? (
              <>
                <div className="cluster">
                  <StatusBadge status={textValue(asRecord(selectedSource.metadata_json).review_status) || "unreviewed"} />
                  <span className="meta-pill mono">Source {selectedSource.id}</span>
                  <span className="meta-pill">Connector: {textValue(selectedSource.connector_name) || "manual"}</span>
                </div>
                <div className="form-field">
                  <label htmlFor="vnext-source-title-edit">Selected source title</label>
                  <input
                    id="vnext-source-title-edit"
                    value={sourceTitleDraft}
                    onChange={(event) => setSourceTitleDraft(event.target.value)}
                  />
                </div>
                <div className="form-field-group form-field-group--two-up">
                  <div className="form-field">
                    <label htmlFor="vnext-source-domain-edit">Source domain</label>
                    <select
                      id="vnext-source-domain-edit"
                      value={sourceDomainDraft}
                      onChange={(event) => setSourceDomainDraft(event.target.value as Domain)}
                    >
                      {VNEXT_DOMAIN_OPTIONS.map((domain) => (
                        <option key={domain.value} value={domain.value}>{domain.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-field">
                    <label htmlFor="vnext-source-sensitivity-edit">Source sensitivity</label>
                    <select
                      id="vnext-source-sensitivity-edit"
                      value={sourceSensitivityDraft}
                      onChange={(event) => setSourceSensitivityDraft(event.target.value as Sensitivity)}
                    >
                      {VNEXT_SENSITIVITY_OPTIONS.map((sensitivity) => (
                        <option key={sensitivity.value} value={sensitivity.value}>{sensitivity.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="form-field">
                  <label htmlFor="vnext-source-project-edit">Source project</label>
                  <select
                    id="vnext-source-project-edit"
                    value={sourceProjectDraft}
                    onChange={(event) => setSourceProjectDraft(event.target.value)}
                  >
                    <option value="">No project</option>
                    {workspace.projects.map((project) => (
                      <option key={project.id} value={project.id}>{project.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="vnext-source-review-note">Review note</label>
                  <textarea
                    id="vnext-source-review-note"
                    value={sourceReviewNote}
                    onChange={(event) => setSourceReviewNote(event.target.value)}
                  />
                </div>
                <div className="vnext-review-actions">
                  <button type="button" className="button" onClick={() => void handleSourceAction("review")} disabled={Boolean(pendingAction)}>Mark reviewed</button>
                  <button type="button" className="button-secondary" onClick={() => void handleSourceAction("update")} disabled={Boolean(pendingAction)}>Save source update</button>
                  <button type="button" className="button-secondary" onClick={() => void handleSourceAction("assign_project")} disabled={Boolean(pendingAction || !sourceProjectDraft)}>Assign source project</button>
                  <button type="button" className="button-secondary" onClick={() => void handleCreateOpenLoopFromSource()} disabled={Boolean(pendingAction)}>Create source open loop</button>
                  <button type="button" className="button-secondary button-secondary--danger" onClick={() => void handleSourceAction("archive")} disabled={Boolean(pendingAction)}>Archive source</button>
                </div>
                <dl className="key-value-grid">
                  <div>
                    <dt>Raw evidence</dt>
                    <dd>{sourceText(selectedSource).slice(0, 600)}</dd>
                  </div>
                  <div>
                    <dt>Chunks</dt>
                    <dd>{selectedSourceTrace?.summary.chunk_count ?? 0}</dd>
                  </div>
                  <div>
                    <dt>Candidate memories</dt>
                    <dd>{selectedSourceTrace?.summary.candidate_memory_count ?? 0}</dd>
                  </div>
                  <div>
                    <dt>Artifacts</dt>
                    <dd>{selectedSourceTrace?.summary.artifact_count ?? 0}</dd>
                  </div>
                </dl>
              </>
            ) : (
              <EmptyState title="No selected source" description="Capture or select source evidence before reviewing it." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Inbox"
          title="Candidate memories"
          description="The live review list is backed by vNext memory rows and preserves source/provenance metadata."
        >
          <div className="list-rows">
            {workspace.reviewItems.length ? (
              workspace.reviewItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`list-row vnext-review-button${selectedReview?.id === item.id ? " is-selected" : ""}`}
                  onClick={() => setSelectedReviewId(item.id)}
                >
                  <span className="list-row__topline">
                    <span className="detail-stack">
                      <span className="list-row__eyebrow mono">{item.memory_type}</span>
                      <span className="list-row__title">{memoryText(item)}</span>
                    </span>
                    <StatusBadge status={item.status ?? "candidate"} />
                  </span>
                  <span className="list-row__meta">
                    <span className="meta-pill">Domain: {domainLabel(asDomain(item.domain))}</span>
                    <span className="meta-pill">Sensitivity: {sensitivityLabel(asSensitivity(item.sensitivity))}</span>
                    {memoryProvenanceLabel(item) ? (
                      <span className="meta-pill">{memoryProvenanceLabel(item)}</span>
                    ) : null}
                  </span>
                </button>
              ))
            ) : (
              <EmptyState title="No memory candidates" description="Candidate memories will appear after source capture extracts claims, decisions, or open loops." />
            )}
          </div>
        </SectionCard>
      </div>

      <div id="vnext-ask-alice" className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Ask Alice"
          title="Evidence-first answer"
          description="Live Ask Alice calls the context-pack endpoint and renders selected memories, source provenance, contradictions, and retrieval rationale."
        >
          <form className="detail-stack" onSubmit={askAlice}>
            <div className="form-field">
              <label htmlFor="vnext-ask-question">Ask Alice question</label>
              <textarea
                id="vnext-ask-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
              />
            </div>
            <button type="submit" className="button" disabled={Boolean(pendingAction)}>
              Ask Alice
            </button>
          </form>

          <div className="transcript-entry transcript-entry--assistant" aria-live="polite">
            <div className="transcript-entry__heading">
              <span className="transcript-entry__role transcript-entry__role--assistant">Alice answer</span>
              <span className="meta-pill">Domain: {domainLabel(answer.domain)}</span>
              <span className="meta-pill">Sensitivity: {sensitivityLabel(answer.sensitivity)}</span>
            </div>
            <p className="response-copy">{answer.summary}</p>
            <dl className="key-value-grid">
              <div>
                <dt>Memory sources used</dt>
                <dd>{answer.memoriesUsed.length ? answer.memoriesUsed.join(" ") : "No memory selected yet."}</dd>
              </div>
              <div>
                <dt>Contradictions</dt>
                <dd>{answer.contradictions.join(" ")}</dd>
              </div>
              <div>
                <dt>Why this answer</dt>
                <dd>{answer.why.join(" ")}</dd>
              </div>
              <div>
                <dt>Sources</dt>
                <dd>{summarizeSources(answer.sources)}</dd>
              </div>
            </dl>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Generated"
          title="Artifacts with review actions"
          description="Generated artifacts are live rows and remain reviewable outputs unless the user explicitly reviews, promotes, or archives them."
        >
          <div id="vnext-generated" className="list-rows">
            {workspace.artifacts.length ? (
              workspace.artifacts.map((artifact) => (
                <article key={artifact.id} className="list-row">
                  <div className="list-row__topline">
                    <div>
                      <span className="list-row__eyebrow mono">{artifact.artifact_type}</span>
                      <h3 className="list-row__title">{artifact.title}</h3>
                    </div>
                    <StatusBadge status={artifact.status ?? "draft"} />
                  </div>
                  <p>{artifactExcerpt(artifact)}</p>
                  <div className="list-row__meta">
                    <span className="meta-pill">Domain: {domainLabel(asDomain(artifact.domain))}</span>
                    <span className="meta-pill">Sensitivity: {sensitivityLabel(asSensitivity(artifact.sensitivity))}</span>
                    <span className="meta-pill">Generated by: {artifact.generated_by}</span>
                    <span className="meta-pill">Mode: {artifactGenerationMode(artifact)}</span>
                    {textValue(asRecord(artifact.metadata_json).scheduler_run_id) ? (
                      <span className="meta-pill mono">Run {textValue(asRecord(artifact.metadata_json).scheduler_run_id)}</span>
                    ) : null}
                    {textValue(asRecord(artifact.metadata_json).trace_id) ? (
                      <span className="meta-pill mono">Trace {textValue(asRecord(artifact.metadata_json).trace_id)}</span>
                    ) : null}
                    {artifactGenerationMode(artifact) === "model_backed" ? (
                      <span className="meta-pill">Model: {artifactModelLabel(artifact)}</span>
                    ) : null}
                  </div>
                  <div className="vnext-review-actions">
                    {(["review", "accept", "reject", "promote", "archive"] as const).map((action) => (
                      <button
                        key={action}
                        type="button"
                        className={action === "reject" ? "button-secondary button-secondary--danger" : "button-secondary"}
                        onClick={() => void handleArtifactAction(artifact, action)}
                        disabled={Boolean(pendingAction)}
                      >
                        {action}
                      </button>
                    ))}
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title="No generated artifacts" description="Generate a daily brief, weekly synthesis, or project update to create reviewable artifacts." />
            )}
          </div>
          <form className="detail-stack" onSubmit={handleQualityRating}>
            <div className="form-field-group form-field-group--two-up">
              <div className="form-field">
                <label htmlFor="vnext-quality-artifact">Quality artifact</label>
                <select
                  id="vnext-quality-artifact"
                  value={qualityArtifactId || workspace.artifacts[0]?.id || ""}
                  onChange={(event) => setQualityArtifactId(event.target.value)}
                >
                  {workspace.artifacts.map((artifact) => (
                    <option key={artifact.id} value={artifact.id}>
                      {artifact.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="vnext-quality-verbosity">Depth</label>
                <select
                  id="vnext-quality-verbosity"
                  value={qualityVerbosity}
                  onChange={(event) => setQualityVerbosity(event.target.value)}
                >
                  <option value="too_shallow">Too shallow</option>
                  <option value="right_sized">Right sized</option>
                  <option value="too_verbose">Too verbose</option>
                  <option value="unknown">Unknown</option>
                </select>
              </div>
            </div>
            <div className="form-field-group form-field-group--three-up">
              {(["usefulness", "accuracy", "source_grounding", "novel_connections", "actionability", "hallucination_risk"] as const).map((field) => (
                <div className="form-field" key={field}>
                  <label htmlFor={`vnext-quality-${field}`}>{field.replace(/_/g, " ")}</label>
                  <input
                    id={`vnext-quality-${field}`}
                    type="number"
                    min={1}
                    max={5}
                    value={qualityScores[field]}
                    onChange={(event) =>
                      setQualityScores((previous) => ({
                        ...previous,
                        [field]: Number(event.target.value),
                      }))
                    }
                  />
                </div>
              ))}
            </div>
            <div className="form-field">
              <label htmlFor="vnext-quality-comments">Comments</label>
              <textarea
                id="vnext-quality-comments"
                value={qualityComments}
                onChange={(event) => setQualityComments(event.target.value)}
              />
            </div>
            <button type="submit" className="button" disabled={Boolean(pendingAction) || workspace.artifacts.length === 0}>
              Save quality rating
            </button>
            <p className="muted-copy">{workspace.qualityEvals.length} quality rating(s) recorded.</p>
          </form>
        </SectionCard>
      </div>

      <div id="vnext-model-comparison" className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Comparison"
          title="Deterministic vs model-backed"
          description="Daily brief, connection report, and contradiction report can be reviewed side by side before any artifact is promoted."
        >
          <div className="list-rows">
            {COMPARISON_ARTIFACT_TYPES.map(({ artifactType, label }) => {
              const deterministic = latestArtifactByMode(workspace.artifacts, artifactType, "deterministic");
              const modelBacked = latestArtifactByMode(workspace.artifacts, artifactType, "model_backed");
              return (
                <article key={artifactType} className="list-row">
                  <div className="list-row__topline">
                    <h3 className="list-row__title">{label}</h3>
                    <StatusBadge status={modelBacked ? "active" : "requires_review"} label={modelBacked ? "Comparable" : "Needs model-backed run"} />
                  </div>
                  <dl className="key-value-grid">
                    <div>
                      <dt>Deterministic</dt>
                      <dd>{deterministic ? artifactExcerpt(deterministic) : "No deterministic artifact yet."}</dd>
                    </div>
                    <div>
                      <dt>Model-backed</dt>
                      <dd>{modelBacked ? artifactExcerpt(modelBacked) : "No model-backed artifact yet."}</dd>
                    </div>
                  </dl>
                  <div className="list-row__meta">
                    <span className="meta-pill">Deterministic: {deterministic?.id ?? "none"}</span>
                    <span className="meta-pill">Model-backed: {modelBacked?.id ?? "none"}</span>
                  </div>
                </article>
              );
            })}
          </div>
        </SectionCard>
      </div>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Daily Brief"
          title="Daily brief"
          description="The generation button creates a live artifact and keeps it in review state."
        >
          <div id="vnext-daily-brief" className="detail-stack">
            <button type="button" className="button" onClick={() => void handleGenerateArtifact("daily")} disabled={Boolean(pendingAction)}>
              Generate daily brief
            </button>
            {dailyArtifact ? (
              <article className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{dailyArtifact.title}</h3>
                  <StatusBadge status={dailyArtifact.status ?? "needs_review"} />
                </div>
                <p>{artifactExcerpt(dailyArtifact)}</p>
              </article>
            ) : (
              <EmptyState title="No daily brief yet" description="Generate the first live daily brief after capturing source evidence." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Weekly Synthesis"
          title="Weekly synthesis"
          description="The weekly synthesis uses source, memory, loop, and artifact evidence and produces a reviewable artifact."
        >
          <div id="vnext-weekly-synthesis" className="detail-stack">
            <button type="button" className="button" onClick={() => void handleGenerateArtifact("weekly")} disabled={Boolean(pendingAction)}>
              Generate weekly synthesis
            </button>
            {weeklyArtifact ? (
              <article className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{weeklyArtifact.title}</h3>
                  <StatusBadge status={weeklyArtifact.status ?? "needs_review"} />
                </div>
                <p>{artifactExcerpt(weeklyArtifact)}</p>
              </article>
            ) : (
              <EmptyState title="No weekly synthesis yet" description="Generate a weekly synthesis when the workspace has evidence to summarize." />
            )}
          </div>
        </SectionCard>
      </div>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Queue"
          title="Work queue"
          description="Queue rows are read-only in this sprint; generated output remains separately reviewable."
        >
          <div id="vnext-queue" className="list-rows">
            {workspace.tasks.length ? (
              workspace.tasks.map((task) => (
                <article key={task.id} className="list-row">
                  <div className="list-row__topline">
                    <h3 className="list-row__title">{task.title}</h3>
                    <StatusBadge status={task.status ?? "pending"} />
                  </div>
                  <div className="list-row__meta">
                    <span className="meta-pill">Type: {task.task_type}</span>
                    <span className="meta-pill">Policy: {task.write_policy ?? "proposal_only"}</span>
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title="Queue is empty" description="Queue items will appear when vNext task workflows enqueue work." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Memory Review"
          title="Selected memory candidate"
          description="Review actions write to the backend memory row, append a revision, and keep provenance metadata intact."
        >
          <div id="vnext-memory-review" className="detail-stack">
            {selectedReview ? (
              <>
                <div className="cluster">
                  <StatusBadge status={selectedReview.status ?? "candidate"} />
                  <span className="meta-pill">Memory: {selectedReview.id}</span>
                </div>
                <div className="form-field">
                  <label htmlFor="vnext-review-title">Edited memory title</label>
                  <textarea id="vnext-review-title" value={draftTitle} onChange={(event) => setDraftTitle(event.target.value)} />
                </div>
                <div className="form-field">
                  <label htmlFor="vnext-review-text">Edited memory text</label>
                  <textarea id="vnext-review-text" value={draftText} onChange={(event) => setDraftText(event.target.value)} />
                </div>
                <div className="form-field-group form-field-group--two-up">
                  <div className="form-field">
                    <label htmlFor="vnext-domain">Domain label</label>
                    <select id="vnext-domain" value={draftDomain} onChange={(event) => setDraftDomain(event.target.value as Domain)}>
                      {VNEXT_DOMAIN_OPTIONS.map((domain) => (
                        <option key={domain.value} value={domain.value}>{domain.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-field">
                    <label htmlFor="vnext-sensitivity">Sensitivity label</label>
                    <select id="vnext-sensitivity" value={draftSensitivity} onChange={(event) => setDraftSensitivity(event.target.value as Sensitivity)}>
                      {VNEXT_SENSITIVITY_OPTIONS.map((sensitivity) => (
                        <option key={sensitivity.value} value={sensitivity.value}>{sensitivity.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="form-field">
                  <label htmlFor="vnext-project">Assigned project</label>
                  <select id="vnext-project" value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}>
                    <option value="">No project</option>
                    {workspace.projects.map((project) => (
                      <option key={project.id} value={project.id}>{project.name}</option>
                    ))}
                  </select>
                </div>
                <div className="vnext-review-actions">
                  <button type="button" className="button" onClick={() => void handleMemoryAction("accept")} disabled={Boolean(pendingAction)}>Accept</button>
                  <button type="button" className="button-secondary" onClick={() => void handleMemoryAction("edit")} disabled={Boolean(pendingAction)}>Save edit</button>
                  <button type="button" className="button-secondary" onClick={() => void handleMemoryAction("private")} disabled={Boolean(pendingAction)}>Mark private</button>
                  <button type="button" className="button-secondary" onClick={() => void handleMemoryAction("assign_project")} disabled={Boolean(pendingAction || !selectedProjectId)}>Assign project</button>
                  <button type="button" className="button-secondary" onClick={() => void handleMemoryAction("promote")} disabled={Boolean(pendingAction)}>Promote</button>
                  <button type="button" className="button-secondary button-secondary--danger" onClick={() => void handleMemoryAction("reject")} disabled={Boolean(pendingAction)}>Reject</button>
                </div>
                <div className="form-field-group">
                  <div className="form-field">
                    <label htmlFor="vnext-open-loop">Open-loop title</label>
                    <input id="vnext-open-loop" value={openLoopTitle} onChange={(event) => setOpenLoopTitle(event.target.value)} />
                  </div>
                  <div className="form-field">
                    <label htmlFor="vnext-open-loop-description">Open-loop description</label>
                    <textarea id="vnext-open-loop-description" value={openLoopDescription} onChange={(event) => setOpenLoopDescription(event.target.value)} />
                  </div>
                  <button type="button" className="button-secondary" onClick={() => void handleCreateOpenLoop()} disabled={Boolean(pendingAction)}>
                    Create open loop from selected memory
                  </button>
                </div>
              </>
            ) : (
              <EmptyState title="No selected memory" description="Capture a note or select a candidate memory from the inbox." />
            )}
          </div>
        </SectionCard>
      </div>

      <div id="vnext-projects" className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Projects"
          title="Project dashboards"
          description="Project cards read live dashboard counts and project update candidates."
        >
          <form className="detail-stack" onSubmit={handleCreateProject}>
            <div className="form-field-group form-field-group--two-up">
              <div className="form-field">
                <label htmlFor="vnext-project-name">Project name</label>
                <input id="vnext-project-name" value={newProjectName} onChange={(event) => setNewProjectName(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="vnext-project-state">Current state</label>
                <input id="vnext-project-state" value={newProjectState} onChange={(event) => setNewProjectState(event.target.value)} />
              </div>
            </div>
            <button type="submit" className="button-secondary" disabled={Boolean(pendingAction)}>Create project</button>
          </form>
          <button type="button" className="button" onClick={() => void handleGenerateArtifact("project")} disabled={Boolean(pendingAction || !workspace.projects.length)}>
            Generate project update candidate
          </button>
          <div className="list-rows">
            {workspace.projectDashboards.length ? (
              workspace.projectDashboards.map((dashboard) => (
                <article key={dashboard.project.id} className="list-row">
                  <div className="list-row__topline">
                    <h3 className="list-row__title">{dashboard.project.name}</h3>
                    <StatusBadge status={dashboard.project.status ?? "active"} />
                  </div>
                  <p>{dashboard.state || dashboard.project.current_state || "No current state recorded."}</p>
                  <div className="list-row__meta">
                    <span className="meta-pill">Memories: {dashboard.counts.memories}</span>
                    <span className="meta-pill">Open loops: {dashboard.counts.open_loops}</span>
                    <span className="meta-pill">Artifacts: {dashboard.counts.artifacts}</span>
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title="No projects" description="Create a project to make project dashboard updates visible." />
            )}
          </div>
          {projectUpdateArtifacts.length ? (
            <p className="muted-copy">{projectUpdateArtifacts.length} project update candidate artifact(s) are awaiting review.</p>
          ) : null}
        </SectionCard>

        <SectionCard
          eyebrow="People"
          title="People graph"
          description="People remain read-only for this sprint while live records are displayed when present."
        >
          <div id="vnext-people" className="list-rows">
            {workspace.people.length ? (
              workspace.people.map((person) => (
                <article key={person.id} className="list-row">
                  <div className="list-row__topline">
                    <h3 className="list-row__title">{person.name}</h3>
                    <span className="meta-pill">Sensitivity: {sensitivityLabel(asSensitivity(person.sensitivity))}</span>
                  </div>
                  <p>{person.relationship_type || person.organization || "No relationship details recorded."}</p>
                  <p className="responsive-note">Evidence: {person.notes || "No notes yet."}</p>
                </article>
              ))
            ) : (
              <EmptyState title="No people records" description="People records are read-only here and will appear when vNext extraction creates them." />
            )}
          </div>
        </SectionCard>
      </div>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Beliefs"
          title="Belief review"
          description="Beliefs are visible but read-only in this live-backed sprint."
        >
          <div id="vnext-beliefs" className="list-rows">
            {workspace.beliefs.length ? (
              workspace.beliefs.map((belief) => (
                <article key={belief.id} className="list-row">
                  <div className="list-row__topline">
                    <h3 className="list-row__title">{belief.claim}</h3>
                    <StatusBadge status={belief.status ?? "emerging"} />
                  </div>
                  <div className="list-row__meta">
                    <span className="meta-pill">Confidence: {belief.confidence ?? "unknown"}</span>
                    <span className="meta-pill">Memory: {belief.memory_id ?? "unlinked"}</span>
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title="No beliefs" description="Beliefs will appear after belief or contradiction workflows create review records." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Open Loops"
          title="Due and waiting items"
          description="Open loops support live close, snooze, edit, and reopen actions."
        >
          <div id="vnext-open-loops" className="detail-stack">
            <div className="list-rows">
              {workspace.openLoops.length ? (
                workspace.openLoops.map((loop) => (
                  <button
                    key={loop.id}
                    type="button"
                    className={`list-row vnext-review-button${selectedLoop?.id === loop.id ? " is-selected" : ""}`}
                    onClick={() => {
                      setSelectedOpenLoopId(loop.id);
                      setOpenLoopTitle(loop.title);
                      setOpenLoopDescription(loop.description ?? "");
                      setOpenLoopDueAt(loop.due_at ?? "");
                      setOpenLoopPriority(loop.priority ?? "normal");
                    }}
                  >
                    <span className="list-row__topline">
                      <span className="list-row__title">{loop.title}</span>
                      <StatusBadge status={loop.status ?? "open"} />
                    </span>
                    <span className="list-row__meta">
                      <span className="meta-pill">Priority: {loop.priority ?? "normal"}</span>
                      <span className="meta-pill">Due: {loop.due_at ?? "unscheduled"}</span>
                    </span>
                  </button>
                ))
              ) : (
                <EmptyState title="No open loops" description="Create one from memory review or generate a daily brief that extracts candidates." />
              )}
            </div>
            {selectedLoop ? (
              <div className="detail-stack">
                <div className="form-field-group form-field-group--two-up">
                  <div className="form-field">
                    <label htmlFor="vnext-loop-title-edit">Selected loop title</label>
                    <input id="vnext-loop-title-edit" value={openLoopTitle} onChange={(event) => setOpenLoopTitle(event.target.value)} />
                  </div>
                  <div className="form-field">
                    <label htmlFor="vnext-loop-due">Due at</label>
                    <input id="vnext-loop-due" value={openLoopDueAt} onChange={(event) => setOpenLoopDueAt(event.target.value)} placeholder="2026-05-11T17:00:00Z" />
                  </div>
                </div>
                <div className="form-field">
                  <label htmlFor="vnext-loop-priority">Priority</label>
                  <select id="vnext-loop-priority" value={openLoopPriority} onChange={(event) => setOpenLoopPriority(event.target.value)}>
                    <option value="low">Low</option>
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
                <div className="vnext-review-actions">
                  <button type="button" className="button-secondary" onClick={() => void handleOpenLoopAction("edit")} disabled={Boolean(pendingAction)}>Save loop edit</button>
                  <button type="button" className="button-secondary" onClick={() => void handleOpenLoopAction("snooze")} disabled={Boolean(pendingAction || !openLoopDueAt)}>Snooze</button>
                  <button type="button" className="button-secondary" onClick={() => void handleOpenLoopAction("reopen")} disabled={Boolean(pendingAction)}>Reopen</button>
                  <button type="button" className="button-secondary button-secondary--danger" onClick={() => void handleOpenLoopAction("close")} disabled={Boolean(pendingAction)}>Close</button>
                </div>
              </div>
            ) : null}
          </div>
        </SectionCard>
      </div>

      <div id="vnext-agent-activity" className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Agent Activity"
          title="Agents and policy posture"
          description="Agent-originated requests keep identity, scope, permission profile, and policy outcomes visible to the operator."
        >
          <div className="list-rows">
            {workspace.agentActivity.agents.length ? (
              workspace.agentActivity.agents.map((agent) => (
                <article key={agent.id} className="list-row">
                  <div className="list-row__topline">
                    <div>
                      <span className="list-row__eyebrow mono">{agent.agent_type}</span>
                      <h3 className="list-row__title">{agentDisplayName(agent.agent_id)}</h3>
                    </div>
                    <StatusBadge status={agent.permission_profile} />
                  </div>
                  <div className="list-row__meta">
                    <span className="meta-pill mono">{agent.agent_id}</span>
                    <span className="meta-pill">Scope: {Array.isArray(agent.project_scope_json) && agent.project_scope_json.length ? agent.project_scope_json.join(", ") : "none"}</span>
                    <span className="meta-pill">Updated: {agent.updated_at ?? "unknown"}</span>
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title="No agent identities yet" description="Agent identities appear after MCP, API, or CLI calls include agent metadata." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Agent Activity"
          title="Recent agent events"
          description="Context packs, artifacts, tasks, memory proposals, open loops, project updates, and policy decisions are auditable here."
        >
          <div className="list-rows">
            {workspace.agentActivity.recent_events.length ? (
              workspace.agentActivity.recent_events.slice(0, 8).map((event) => (
                <article key={event.id} className="list-row">
                  <div className="list-row__topline">
                    <div>
                      <span className="list-row__eyebrow mono">{event.occurred_at}</span>
                      <h3 className="list-row__title">{event.event_type}</h3>
                    </div>
                    <StatusBadge status={event.actor_id ?? event.actor_type} />
                  </div>
                  <div className="list-row__meta">
                    <span className="meta-pill">Target: {event.target_type ? `${event.target_type}:${event.target_id}` : "workspace"}</span>
                    {event.trace_id ? <span className="meta-pill mono">Trace {event.trace_id}</span> : null}
                    {event.run_id ? <span className="meta-pill mono">Run {event.run_id}</span> : null}
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title="No agent events" description="Agent context packs, proposals, generated artifacts, and queue activity will appear here." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Agent Activity"
          title="Trusted memory commits"
          description="Auto-committed, inline-confirmed, corrected, undone, and forgotten agent memories remain auditable here."
        >
          <div className="list-rows">
            {workspace.agentActivity.recent_commits.length ? (
              workspace.agentActivity.recent_commits.slice(0, 8).map((memory) => {
                const agentic = agenticMemoryMetadata(memory);
                const identity = asRecord(agentic.agent_identity);
                return (
                  <article key={`agentic-commit-${memory.id}`} className="list-row">
                    <div className="list-row__topline">
                      <div>
                        <span className="list-row__eyebrow mono">{textValue(agentic.write_mode) || "memory commit"}</span>
                        <h3 className="list-row__title">{memoryText(memory)}</h3>
                      </div>
                      <StatusBadge status={textValue(agentic.lifecycle_status) || memory.status || "active"} />
                    </div>
                    <div className="list-row__meta">
                      <span className="meta-pill">Agent: {textValue(identity.agent_id) || textValue(memory.metadata_json?.agent_id) || "unknown"}</span>
                      <span className="meta-pill">Domain: {memory.domain ?? "unknown"}</span>
                      <span className="meta-pill">Sensitivity: {memory.sensitivity ?? "unknown"}</span>
                    </div>
                  </article>
                );
              })
            ) : (
              <EmptyState title="No trusted memory commits" description="Explicit trusted-agent memory commits will appear here with lifecycle status and audit metadata." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Agent Activity"
          title="Inline confirmations"
          description="Sensitive, contradictory, or ambiguous memory writes wait here until confirmed, edited, rejected, or expired."
        >
          <div className="list-rows">
            {workspace.agentActivity.inline_confirmations.length ? (
              workspace.agentActivity.inline_confirmations.slice(0, 6).map((memory) => {
                const agentic = agenticMemoryMetadata(memory);
                const confirmation = asRecord(agentic.confirmation);
                const confirmationId = textValue(confirmation.confirmation_id);
                const draftText = inlineConfirmationDrafts[memory.id] ?? memoryText(memory);
                return (
                  <article key={`inline-confirmation-${memory.id}`} className="list-row">
                    <div className="list-row__topline">
                      <div>
                        <span className="list-row__eyebrow mono">{textValue(confirmation.confirmation_id) || "confirmation"}</span>
                        <h3 className="list-row__title">{memoryText(memory)}</h3>
                      </div>
                      <StatusBadge status={textValue(confirmation.status) || memory.status || "pending"} />
                    </div>
                    <div className="list-row__meta">
                      <span className="meta-pill">Reason: {textValue(confirmation.policy_reason) || "policy gate"}</span>
                      <span className="meta-pill">Expires: {textValue(confirmation.expires_at) || "unknown"}</span>
                    </div>
                    <div className="form-field">
                      <label htmlFor={`inline-confirmation-text-${memory.id}`}>Reviewed memory text</label>
                      <textarea
                        id={`inline-confirmation-text-${memory.id}`}
                        value={draftText}
                        onChange={(event) =>
                          setInlineConfirmationDrafts((previous) => ({
                            ...previous,
                            [memory.id]: event.target.value,
                          }))
                        }
                        disabled={Boolean(pendingAction) || !confirmationId}
                      />
                    </div>
                    <div className="vnext-review-actions" aria-label={`Review confirmation ${confirmationId || memory.id}`}>
                      <button
                        type="button"
                        className="button"
                        onClick={() => void handleInlineConfirmation(memory, "confirm")}
                        disabled={Boolean(pendingAction) || !confirmationId}
                      >
                        Confirm memory
                      </button>
                      <button
                        type="button"
                        className="button-secondary"
                        onClick={() => void handleInlineConfirmation(memory, "edit")}
                        disabled={Boolean(pendingAction) || !confirmationId || !draftText.trim()}
                      >
                        Save edit and confirm
                      </button>
                      <button
                        type="button"
                        className="button-secondary button-secondary--danger"
                        onClick={() => void handleInlineConfirmation(memory, "reject")}
                        disabled={Boolean(pendingAction) || !confirmationId}
                      >
                        Reject memory
                      </button>
                    </div>
                    {dataSource === "fixture" ? (
                      <p className="muted-copy">Demo controls update fixture state only; they never call the configured API.</p>
                    ) : null}
                  </article>
                );
              })
            ) : (
              <EmptyState title="No inline confirmations" description="Sensitive or conflicting memory writes that need confirmation will appear here." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Agent Activity"
          title="Policy blocks and filters"
          description="Blocked and filtered agent requests remain visible for privacy and safety review."
        >
          <div className="list-rows">
            {workspace.agentActivity.policy_blocks.length ? (
              workspace.agentActivity.policy_blocks.map((event) => (
                <article key={event.id} className="list-row">
                  <div className="list-row__topline">
                    <h3 className="list-row__title">{event.event_type}</h3>
                    <StatusBadge status={event.actor_id ?? "agent"} />
                  </div>
                  <p>{JSON.stringify(event.payload_json ?? {})}</p>
                  <div className="list-row__meta">
                    <span className="meta-pill mono">{event.occurred_at}</span>
                    <span className="meta-pill">Target: {event.target_type ?? "policy"}</span>
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title="No policy blocks" description="Restricted or filtered agent requests will be logged here." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Agent Activity"
          title="Policy telemetry"
          description="Aggregated agent policy outcomes show blocks, filters, review gates, workflow triggers, proposals, and artifact generation."
        >
          <dl className="key-value-grid key-value-grid--compact">
            <div>
              <dt>Agent events</dt>
              <dd>{workspace.policyTelemetry.total_agent_events}</dd>
            </div>
            <div>
              <dt>Policy decisions</dt>
              <dd>{workspace.policyTelemetry.total_policy_decisions}</dd>
            </div>
            <div>
              <dt>Filtered agents</dt>
              <dd>{workspace.policyTelemetry.policy_filters_by_agent.length}</dd>
            </div>
            <div>
              <dt>Review-gated agents</dt>
              <dd>{workspace.policyTelemetry.requires_review_by_agent.length}</dd>
            </div>
          </dl>
          <div className="list-rows">
            {workspace.policyTelemetry.restricted_domains_requested.slice(0, 3).map((row) => (
              <article key={`restricted-${textValue(row.domain)}`} className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{textValue(row.domain) || "restricted domain"}</h3>
                  <StatusBadge status={`${row.count} requests`} />
                </div>
              </article>
            ))}
            {workspace.policyTelemetry.workflows_triggered_by_agents.slice(0, 3).map((row) => (
              <article key={`workflow-telemetry-${textValue(row.workflow_type)}`} className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{textValue(row.workflow_type) || "workflow"}</h3>
                  <StatusBadge status={`${row.count} agent runs`} />
                </div>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Agent Activity"
          title="Generated and proposed work"
          description="Agent-generated artifacts and pending review items stay in human review lanes."
        >
          <dl className="key-value-grid key-value-grid--compact">
            <div>
              <dt>Generated artifacts</dt>
              <dd>{workspace.agentActivity.generated_artifacts.length}</dd>
            </div>
            <div>
              <dt>Pending review items</dt>
              <dd>{workspace.agentActivity.pending_review_items.length}</dd>
            </div>
          </dl>
          <div className="list-rows">
            {[...workspace.agentActivity.generated_artifacts.slice(0, 3), ...workspace.agentActivity.pending_review_items.slice(0, 3)].map((item) => (
              <article key={`agent-work-${item.id}`} className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{"artifact_type" in item ? item.title : memoryText(item)}</h3>
                  <StatusBadge status={item.status ?? "needs_review"} />
                </div>
                <div className="list-row__meta">
                  <span className="meta-pill">Domain: {domainLabel(asDomain(item.domain))}</span>
                  <span className="meta-pill">Sensitivity: {sensitivityLabel(asSensitivity(item.sensitivity))}</span>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>
      </div>

      <div id="vnext-schedules" className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Schedules"
          title="Governed scheduler"
          description="Local workflows are disabled by default, policy-checked, pausable, auditable, and produce reviewable artifacts only."
        >
          <div className="cluster">
            <StatusBadge status={workspace.scheduler.disabled_by_default ? "requires_review" : "active"} label={workspace.scheduler.disabled_by_default ? "Disabled by default" : "Configured"} />
            <span className="meta-pill">Mode: {workspace.scheduler.mode}</span>
            <span className="meta-pill">Enabled: {workspace.scheduler.enabled_count}</span>
            <span className="meta-pill">Paused: {workspace.scheduler.paused_count}</span>
            <span className="meta-pill">Daemon: {workspace.scheduler.daemon?.running ? "running" : workspace.scheduler.daemon?.configured ? "stopped" : "not configured"}</span>
          </div>
          <dl className="key-value-grid key-value-grid--compact">
            <div>
              <dt>Last due scan</dt>
              <dd>{workspace.scheduler.daemon?.last_due_scan_at ?? workspace.scheduler.last_due_scan?.occurred_at ?? "never"}</dd>
            </div>
            <div>
              <dt>Last due count</dt>
              <dd>{workspace.scheduler.daemon?.last_due_count ?? (textValue(asRecord(workspace.scheduler.last_due_scan?.payload_json).due_count) || "0")}</dd>
            </div>
            <div>
              <dt>Next due workflow</dt>
              <dd>{workspace.scheduler.next_due_workflow?.workflow_type ?? "none"}</dd>
            </div>
            <div>
              <dt>Running workflow</dt>
              <dd>{workspace.scheduler.currently_running_workflow?.workflow_type ?? "none"}</dd>
            </div>
          </dl>
          <div className="vnext-review-actions">
            <button type="button" className="button" onClick={() => void handleSchedulerRunDue()} disabled={Boolean(pendingAction)}>
              Run due
            </button>
          </div>
          {workspace.scheduler.last_failure ? (
            <article className="list-row">
              <div className="list-row__topline">
                <h3 className="list-row__title">Last scheduler failure</h3>
                <StatusBadge status="failed" />
              </div>
              <p>{workspace.scheduler.last_failure.error_message ?? "No error message recorded."}</p>
            </article>
          ) : null}
          {workspace.scheduler.recent_failures?.length ? (
            <div className="list-rows">
              {workspace.scheduler.recent_failures.slice(0, 3).map((run) => (
                <article key={`scheduler-failure-${run.id}`} className="list-row">
                  <div className="list-row__topline">
                    <h3 className="list-row__title">{run.workflow_type}</h3>
                    <StatusBadge status="failed" />
                  </div>
                  <p>{run.error_message ?? "No error message recorded."}</p>
                </article>
              ))}
            </div>
          ) : null}
          <div className="list-rows">
            {workspace.scheduler.workflows.length ? (
              workspace.scheduler.workflows.map((workflow) => {
                const draft = schedulerDrafts[workflow.workflow_type] ?? {
                  timeOfDay: scheduleValue(workflow, "time_of_day", workflow.workflow_type === "weekly_synthesis" ? "09:00" : "08:00"),
                  dayOfWeek: scheduleValue(workflow, "day_of_week", "monday"),
                  timezone: workflow.timezone || "UTC",
                };
                return (
                  <article key={workflow.id} className="list-row">
                    <div className="list-row__topline">
                      <div>
                        <span className="list-row__eyebrow mono">{workflow.workflow_type}</span>
                        <h3 className="list-row__title">{workflow.workflow_type.replace(/_/g, " ")}</h3>
                      </div>
                      <StatusBadge status={workflow.paused ? "paused" : workflow.enabled ? "active" : "disabled"} />
                    </div>
                    <p>{scheduleSummary(workflow)}</p>
                    <div className="list-row__meta">
                      <span className="meta-pill">Next: {workflow.next_run_at ?? "manual or disabled"}</span>
                      <span className="meta-pill">Last: {workflow.last_run_at ?? "never"}</span>
                      <span className="meta-pill">Last success: {workspace.scheduler.last_success_by_workflow?.[workflow.workflow_type]?.finished_at ?? "never"}</span>
                      <span className="meta-pill">Result: {workflow.last_result ?? "none"}</span>
                      {workflow.last_error ? <span className="meta-pill">Error: {workflow.last_error}</span> : null}
                    </div>
                    {workflow.workflow_type === "daily_brief" || workflow.workflow_type === "weekly_synthesis" ? (
                      <div className="form-field-group form-field-group--two-up">
                        <div className="form-field">
                          <label htmlFor={`vnext-schedule-time-${workflow.workflow_type}`}>Time of day</label>
                          <input
                            id={`vnext-schedule-time-${workflow.workflow_type}`}
                            value={draft.timeOfDay}
                            onChange={(event) =>
                              setSchedulerDrafts((previous) => ({
                                ...previous,
                                [workflow.workflow_type]: { ...draft, timeOfDay: event.target.value },
                              }))
                            }
                            placeholder="08:00"
                          />
                        </div>
                        {workflow.workflow_type === "weekly_synthesis" ? (
                          <div className="form-field">
                            <label htmlFor="vnext-schedule-weekly-day">Weekly day</label>
                            <select
                              id="vnext-schedule-weekly-day"
                              value={draft.dayOfWeek}
                              onChange={(event) =>
                                setSchedulerDrafts((previous) => ({
                                  ...previous,
                                  [workflow.workflow_type]: { ...draft, dayOfWeek: event.target.value },
                                }))
                              }
                            >
                              {["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].map((day) => (
                                <option key={day} value={day}>{day}</option>
                              ))}
                            </select>
                          </div>
                        ) : null}
                        <div className="form-field">
                          <label htmlFor={`vnext-schedule-zone-${workflow.workflow_type}`}>Timezone</label>
                          <input
                            id={`vnext-schedule-zone-${workflow.workflow_type}`}
                            value={draft.timezone}
                            onChange={(event) =>
                              setSchedulerDrafts((previous) => ({
                                ...previous,
                                [workflow.workflow_type]: { ...draft, timezone: event.target.value },
                              }))
                            }
                            placeholder="UTC"
                          />
                        </div>
                      </div>
                    ) : null}
                    <div className="vnext-review-actions">
                      <button type="button" className="button-secondary" onClick={() => void handleSchedulerAction(workflow, workflow.enabled ? "disable" : "enable")} disabled={Boolean(pendingAction)}>
                        {workflow.enabled ? "Disable" : "Enable"}
                      </button>
                      <button type="button" className="button-secondary" onClick={() => void handleSchedulerAction(workflow, workflow.paused ? "resume" : "pause")} disabled={Boolean(pendingAction)}>
                        {workflow.paused ? "Resume" : "Pause"}
                      </button>
                      <button type="button" className="button-secondary" onClick={() => void handleSchedulerAction(workflow, "update_schedule")} disabled={Boolean(pendingAction)}>
                        Edit schedule
                      </button>
                      <button type="button" className="button" onClick={() => void handleSchedulerAction(workflow, "run_now")} disabled={Boolean(pendingAction)}>
                        Run now
                      </button>
                    </div>
                  </article>
                );
              })
            ) : (
              <EmptyState title="No scheduler workflows" description="The local API will create disabled workflow defaults when live scheduler status is loaded." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Schedules"
          title="Recent scheduler runs"
          description="Run history records workflow, status, run ID, trace ID, output artifact, and failures."
        >
          <div className="timeline-list">
            {workspace.scheduler.recent_runs.length ? (
              workspace.scheduler.recent_runs.map((run) => (
                <article key={run.id} className="timeline-item">
                  <div className="timeline-item__topline">
                    <span className="list-row__eyebrow mono">{run.started_at}</span>
                    <h3 className="list-row__title">{run.workflow_type}</h3>
                  </div>
                  <div className="list-row__meta">
                    <span className="meta-pill">Status: {run.status}</span>
                    <span className="meta-pill mono">Run {run.id}</span>
                    <span className="meta-pill mono">Trace {run.trace_id}</span>
                    <span className="meta-pill">Artifact: {run.artifact_id ?? "none"}</span>
                  </div>
                  {run.error_message ? <p>{run.error_message}</p> : null}
                </article>
              ))
            ) : (
              <EmptyState title="No scheduler runs" description="Manual or scheduled workflow runs will appear here." />
            )}
          </div>
        </SectionCard>
      </div>

      <div className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Timeline"
          title="Brain timeline"
          description="The timeline is a read-only event-log projection for this sprint."
        >
          <div id="vnext-timeline" className="timeline-list">
            {workspace.recentEvents.length ? (
              workspace.recentEvents.map((event) => (
                <article key={`timeline-${event.id}`} className="timeline-item">
                  <div className="timeline-item__topline">
                    <span className="list-row__eyebrow mono">{event.occurred_at}</span>
                    <h3 className="list-row__title">{event.event_type}</h3>
                  </div>
                  <p>{event.target_type ? `${event.target_type}:${event.target_id}` : "workspace event"}</p>
                </article>
              ))
            ) : (
              <EmptyState title="No timeline events" description="Timeline entries appear after live capture, retrieval, generation, or review actions." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Trace"
          title="Capture-to-brief trace"
          description="Follow selected source evidence through chunks, candidate memories, generated artifacts, open loops, ratings, and event-log records."
        >
          <div id="vnext-trace" className="detail-stack">
            {selectedSourceTrace ? (
              <>
                <div className="cluster">
                  <span className="meta-pill mono">{selectedSourceTrace.trace_id}</span>
                  <span className="meta-pill">Chunks: {selectedSourceTrace.summary.chunk_count}</span>
                  <span className="meta-pill">Memories: {selectedSourceTrace.summary.candidate_memory_count}</span>
                  <span className="meta-pill">Artifacts: {selectedSourceTrace.summary.artifact_count}</span>
                  <span className="meta-pill">Events: {selectedSourceTrace.summary.event_count}</span>
                </div>
                <dl className="key-value-grid">
                  <div>
                    <dt>Source</dt>
                    <dd>{selectedSourceTrace.source.title || selectedSourceTrace.source.id}</dd>
                  </div>
                  <div>
                    <dt>Candidate memories</dt>
                    <dd>
                      {selectedSourceTrace.candidate_memories.length
                        ? selectedSourceTrace.candidate_memories.map(memoryText).join(" ")
                        : "No candidate memory linked yet."}
                    </dd>
                  </div>
                  <div>
                    <dt>Generated artifacts</dt>
                    <dd>
                      {selectedSourceTrace.artifacts.length
                        ? selectedSourceTrace.artifacts.map((artifact) => artifact.title || artifact.id).join(", ")
                        : "No generated artifact references this source yet."}
                    </dd>
                  </div>
                  <div>
                    <dt>Open loops</dt>
                    <dd>
                      {selectedSourceTrace.open_loops.length
                        ? selectedSourceTrace.open_loops.map((loop) => loop.title).join(", ")
                        : "No open loop linked yet."}
                    </dd>
                  </div>
                </dl>
                <div className="timeline-list">
                  {selectedSourceTrace.events.slice(0, 6).map((event) => (
                    <article key={`trace-event-${event.id}`} className="timeline-item">
                      <div className="timeline-item__topline">
                        <span className="list-row__eyebrow mono">{event.occurred_at}</span>
                        <h3 className="list-row__title">{event.event_type}</h3>
                      </div>
                      <p>{event.target_type ? `${event.target_type}:${event.target_id}` : "workspace event"}</p>
                    </article>
                  ))}
                </div>
              </>
            ) : (
              <EmptyState title="No source trace" description="Select a source with linked candidates or artifacts to inspect its capture-to-brief path." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Graph"
          title="Connection graph"
          description="Graph visualization remains lightweight and read-only; live graph polish is deferred."
        >
          <div id="vnext-graph" className="vnext-graph-grid">
            <div className="vnext-graph-canvas" role="img" aria-label="Graph preview">
              {[...workspace.projects.map((project) => project.name), ...workspace.people.map((person) => person.name)]
                .slice(0, 5)
                .map((node, index) => (
                  <span key={`${node}-${index}`} className={`vnext-graph-node vnext-graph-node--${index + 1}`}>
                    {node}
                  </span>
                ))}
            </div>
            <div className="detail-stack">
              <div className="cluster">
                <span className="meta-pill">Nodes: {workspace.projects.length + workspace.people.length}</span>
                <span className="meta-pill">Live graph write actions deferred</span>
              </div>
            </div>
          </div>
        </SectionCard>
      </div>

      <div id="vnext-connectors" className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Connectors"
          title="Connector settings"
          description="Live capture connectors expose editable defaults, secret_ref status, cursors, failures, dedupe, and last sync posture."
        >
          <form className="detail-stack" onSubmit={handleSaveConnectorSettings}>
            <div className="form-grid">
              <div className="form-field">
                <label htmlFor="vnext-connector-select">Connector</label>
                <select
                  id="vnext-connector-select"
                  value={selectedConnectorId}
                  onChange={(event) => setSelectedConnectorId(event.target.value)}
                >
                  {INITIAL_CONNECTORS.map((connector) => (
                    <option key={connector.id} value={connector.id}>
                      {connector.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="vnext-connector-enabled">Enabled</label>
                <select
                  id="vnext-connector-enabled"
                  value={connectorEnabled ? "enabled" : "disabled"}
                  onChange={(event) => setConnectorEnabled(event.target.value === "enabled")}
                >
                  <option value="enabled">Enabled</option>
                  <option value="disabled">Disabled</option>
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="vnext-connector-domain">Default domain</label>
                <select
                  id="vnext-connector-domain"
                  value={connectorDomain}
                  onChange={(event) => setConnectorDomain(event.target.value as Domain)}
                >
                  {VNEXT_DOMAIN_OPTIONS.map((domain) => (
                    <option key={domain.value} value={domain.value}>
                      {domain.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="vnext-connector-sensitivity">Default sensitivity</label>
                <select
                  id="vnext-connector-sensitivity"
                  value={connectorSensitivity}
                  onChange={(event) => setConnectorSensitivity(event.target.value as Sensitivity)}
                >
                  {VNEXT_SENSITIVITY_OPTIONS.map((sensitivity) => (
                    <option key={sensitivity.value} value={sensitivity.value}>
                      {sensitivity.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {(selectedConnector.id === "telegram" || selectedConnector.id === "browser_clipper") ? (
              <div className="form-field">
                <label htmlFor="vnext-connector-secret-ref">Secret ref</label>
                <input
                  id="vnext-connector-secret-ref"
                  value={connectorSecretRef}
                  onChange={(event) => setConnectorSecretRef(event.target.value)}
                  placeholder="telegram.bot_token.default"
                />
              </div>
            ) : null}
            {selectedConnector.id === "telegram" ? (
              <div className="form-field">
                <label htmlFor="vnext-telegram-chat-ids">Allowed chat IDs</label>
                <textarea
                  id="vnext-telegram-chat-ids"
                  value={telegramAllowedChats}
                  onChange={(event) => setTelegramAllowedChats(event.target.value)}
                />
              </div>
            ) : null}
            {selectedConnector.id === "local_folder" ? (
              <div className="form-grid">
                <div className="form-field">
                  <label htmlFor="vnext-local-folder-path">Watched path</label>
                  <input
                    id="vnext-local-folder-path"
                    value={localFolderPath}
                    onChange={(event) => setLocalFolderPath(event.target.value)}
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="vnext-local-folder-extensions">Extensions</label>
                  <input
                    id="vnext-local-folder-extensions"
                    value={localFolderExtensions}
                    onChange={(event) => setLocalFolderExtensions(event.target.value)}
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="vnext-local-folder-ignores">Ignore patterns</label>
                  <input
                    id="vnext-local-folder-ignores"
                    value={localFolderIgnores}
                    onChange={(event) => setLocalFolderIgnores(event.target.value)}
                  />
                </div>
              </div>
            ) : null}
            <div className="button-row">
              <button type="submit" className="primary-action">Save connector settings</button>
              {(selectedConnector.id === "telegram" || selectedConnector.id === "local_folder") ? (
                <button type="button" onClick={handleRunConnectorSync}>Run sync now</button>
              ) : null}
            </div>
          </form>
          <div className="list-rows">
            {INITIAL_CONNECTORS.map((connector) => (
              <article key={connector.id} className="list-row">
                <div className="list-row__topline">
                  <h3 className="list-row__title">{connector.name}</h3>
                  <StatusBadge
                    status={connectorHealth(workspace, connector.id)?.enabled ? "accepted" : "needs_review"}
                    label={connectorHealth(workspace, connector.id)?.enabled ? "Enabled" : "Disabled"}
                  />
                </div>
                <div className="list-row__meta">
                  <span className="meta-pill">{connector.stage}</span>
                  <span className="meta-pill">Default domain: {domainLabel(connector.defaultDomain)}</span>
                  <span className="meta-pill">Default sensitivity: {sensitivityLabel(connector.defaultSensitivity)}</span>
                  <span className="meta-pill">Secret: {connectorHealth(workspace, connector.id)?.secret_configured ? "Configured" : "No secret"}</span>
                  <span className="meta-pill">Captured: {connectorHealth(workspace, connector.id)?.items_captured ?? 0}</span>
                  <span className="meta-pill">Failed: {connectorHealth(workspace, connector.id)?.items_failed ?? 0}</span>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Selected Connector"
          title="Connector details"
          description="Cursor posture and evidence handling are visible before live polling is added."
        >
          <dl className="key-value-grid key-value-grid--compact">
            <div>
              <dt>Cursor</dt>
              <dd>{connectorHealth(workspace, selectedConnector.id)?.cursor_state ?? selectedConnector.cursor}</dd>
            </div>
            <div>
              <dt>Last sync</dt>
              <dd>{connectorHealth(workspace, selectedConnector.id)?.last_sync_at ?? "No sync yet"}</dd>
            </div>
            <div>
              <dt>Failure posture</dt>
              <dd>{connectorHealth(workspace, selectedConnector.id)?.last_error ?? selectedConnector.failureMode}</dd>
            </div>
            <div>
              <dt>Sync mode</dt>
              <dd>{connectorHealth(workspace, selectedConnector.id)?.sync_mode ?? "manual"}</dd>
            </div>
            <div>
              <dt>Browser Clipper</dt>
              <dd>{browserClipperEndpoint}</dd>
            </div>
          </dl>
          {selectedConnector.id === "browser_clipper" ? (
            <div className="detail-stack">
              <div className="form-field">
                <label htmlFor="vnext-browser-bookmarklet">Bookmarklet</label>
                <textarea id="vnext-browser-bookmarklet" readOnly value={BROWSER_CLIPPER_BOOKMARKLET} />
              </div>
              <p className="section-note">
                The bookmarklet never receives or prompts for an agent API key because it runs in
                the visited page context. It works only in zero-active-key local compatibility
                mode. After provisioning a key, capture with a trusted API client that sends both
                Bearer authentication and the configured capture token.
              </p>
            </div>
          ) : null}
          {selectedConnector.id === "browser_clipper" ? (
            <div className="detail-stack">
              <div className="form-grid">
                <div className="form-field">
                  <label htmlFor="vnext-browser-test-url">Test clip URL</label>
                  <input
                    id="vnext-browser-test-url"
                    value={browserClipUrl}
                    onChange={(event) => setBrowserClipUrl(event.target.value)}
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="vnext-browser-test-selection">Selected text</label>
                  <textarea
                    id="vnext-browser-test-selection"
                    value={browserClipSelection}
                    onChange={(event) => setBrowserClipSelection(event.target.value)}
                  />
                </div>
              </div>
              <div className="button-row">
                <button type="button" onClick={handleTestBrowserClip}>Send test clip</button>
              </div>
            </div>
          ) : null}
        </SectionCard>
      </div>

      <div id="vnext-doctor" className="content-grid content-grid--wide">
        <SectionCard
          eyebrow="Doctor"
          title="Readiness checks"
          description="Doctor checks expose migration, connector settings/state, secret reference, scheduler daemon, and capture pipeline posture."
        >
          <div className="cluster">
            <StatusBadge
              status={workspace.doctor.status === "pass" ? "accepted" : workspace.doctor.status === "fail" ? "failed" : "requires_review"}
              label={`Doctor: ${workspace.doctor.status}`}
            />
            <span className="meta-pill">Blocking: {workspace.doctor.blocking_failure_count}</span>
            <span className="meta-pill">Warnings: {workspace.doctor.warning_count}</span>
            <span className="meta-pill">CI mode: {workspace.doctor.ci_mode ? "on" : "off"}</span>
            <span className="meta-pill">Safe fix: {workspace.doctor.fix_safe_applied ? "applied" : "not applied"}</span>
          </div>
          <div className="vnext-review-actions">
            <button type="button" className="button" onClick={() => void handleRunDoctor(false)} disabled={Boolean(pendingAction)}>
              Run doctor
            </button>
            <button type="button" className="button-secondary" onClick={() => void handleRunDoctor(true)} disabled={Boolean(pendingAction)}>
              Run doctor --fix-safe
            </button>
          </div>
          <div className="list-rows">
            {workspace.doctor.checks.length ? (
              workspace.doctor.checks.map((check) => (
                <article key={check.name} className="list-row">
                  <div className="list-row__topline">
                    <div>
                      <span className="list-row__eyebrow mono">{check.severity}</span>
                      <h3 className="list-row__title">{check.name}</h3>
                    </div>
                    <StatusBadge status={check.status} />
                  </div>
                  <p>{check.message}</p>
                  {check.recommended_fix ? <p className="responsive-note">Fix: {check.recommended_fix}</p> : null}
                </article>
              ))
            ) : (
              <EmptyState title="No doctor checks loaded" description="Run doctor or load live workspace readiness to populate checks." />
            )}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Doctor"
          title="Readiness details"
          description="Dogfood readiness and connector health are shown together so setup issues are visible before daily use."
        >
          <dl className="key-value-grid key-value-grid--compact">
            <div>
              <dt>Dogfood readiness</dt>
              <dd>{workspace.dogfooding.dogfood_readiness?.status ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Migration status</dt>
              <dd>{textValue(workspace.doctor.migration_status["status"]) || "unknown"}</dd>
            </div>
            <div>
              <dt>Connector health rows</dt>
              <dd>{workspace.doctor.connector_health.count}</dd>
            </div>
            <div>
              <dt>Recommended fixes</dt>
              <dd>{workspace.doctor.recommended_fixes.filter(Boolean).length}</dd>
            </div>
          </dl>
          <div className="cluster">
            {workspace.doctor.recommended_fixes.filter(Boolean).map((fix, index) => (
              <span key={`${index}-${String(fix)}`} className="meta-pill">{fix}</span>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        eyebrow="Settings"
        title="Brain Charter"
        description="The Brain Charter is live-readable and live-writable where supported by the vNext settings API."
      >
        <form className="detail-stack" onSubmit={handleSaveCharter}>
          <div className="form-field">
            <label htmlFor="vnext-brain-charter">Brain Charter Markdown</label>
            <textarea
              id="vnext-brain-charter"
              value={charterText}
              onChange={(event) => setCharterText(event.target.value)}
            />
          </div>
          <div className="form-field">
            <label htmlFor="vnext-charter-sensitivity">Charter sensitivity</label>
            <select
              id="vnext-charter-sensitivity"
              value={charterSensitivity}
              onChange={(event) => setCharterSensitivity(event.target.value as Sensitivity)}
            >
              {VNEXT_SENSITIVITY_OPTIONS.map((sensitivity) => (
                <option key={sensitivity.value} value={sensitivity.value}>
                  {sensitivity.label}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" className="button" disabled={Boolean(pendingAction)}>
            Save Brain Charter
          </button>
        </form>
      </SectionCard>

      <SectionCard
        eyebrow="Action Log"
        title="Latest UI actions"
        description="Recent live or demo actions remain visible for review while the event log records backend writes."
      >
        <div className="list-rows">
          {actionLog.map((entry, index) => (
            <div key={`${entry}-${index}`} className="list-row">
              {entry}
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
