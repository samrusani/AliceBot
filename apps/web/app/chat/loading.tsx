import { WorkspaceLoading } from "../../components/workspace-loading";

export default function Loading() {
  return (
    <WorkspaceLoading
      eyebrow="Requests"
      title="Conversation and request workspace"
      description="Loading the selected thread, continuity, workflow, and resumption context."
    />
  );
}
