import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ArtifactChunkList } from "./artifact-chunk-list";

describe("ArtifactChunkList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders idle state when no artifact is selected", () => {
    render(
      <ArtifactChunkList
        artifactId={null}
        chunks={[]}
        summary={null}
        source={null}
      />,
    );

    expect(screen.getByText("Chunk review is idle")).toBeInTheDocument();
  });

  it("renders ordered chunk rows with sequence and evidence text", () => {
    render(
      <ArtifactChunkList
        artifactId="artifact-1"
        chunks={[
          {
            id: "chunk-1",
            task_artifact_id: "artifact-1",
            sequence_no: 1,
            char_start: 0,
            char_end_exclusive: 12,
            text: "alpha chunk",
            created_at: "2026-03-18T00:00:00Z",
            updated_at: "2026-03-18T00:00:00Z",
          },
          {
            id: "chunk-2",
            task_artifact_id: "artifact-1",
            sequence_no: 2,
            char_start: 12,
            char_end_exclusive: 26,
            text: "beta chunk",
            created_at: "2026-03-18T00:00:01Z",
            updated_at: "2026-03-18T00:00:01Z",
          },
        ]}
        summary={{
          total_count: 2,
          total_characters: 26,
          media_type: "text/markdown",
          chunking_rule: "artifact_ingestion_v0",
          order: ["sequence_no_asc", "id_asc"],
        }}
        source="fixture"
      />,
    );

    expect(screen.getByText("Chunk 1")).toBeInTheDocument();
    expect(screen.getByText("Chunk 2")).toBeInTheDocument();
    expect(screen.getByText("alpha chunk")).toBeInTheDocument();
    expect(screen.getByText("beta chunk")).toBeInTheDocument();
    expect(screen.getByText("Fixture chunks")).toBeInTheDocument();
  });
});
