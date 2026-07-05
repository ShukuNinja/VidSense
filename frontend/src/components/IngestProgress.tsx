import { useEffect, useState } from "react";
import { streamIngest } from "../api";
import type { IngestState } from "../types";

const STAGES: [string, string][] = [
  ["download", "Downloading clip"],
  ["audio", "Extracting audio"],
  ["transcribe", "Transcribing"],
  ["chunk", "Generating chunks"],
  ["index", "Building index"],
];

interface Props {
  chatId: number;
  onReady: () => void;
  onFailed: (error: string) => void;
}

export default function IngestProgress({ chatId, onReady, onFailed }: Props) {
  const [state, setState] = useState<IngestState>({
    status: "ingesting",
    stage: null,
    stages_done: [],
  });

  useEffect(() => {
    const ctrl = new AbortController();
    streamIngest(
      chatId,
      (ev: IngestState) => {
        setState(ev);
        if (ev.status === "ready") onReady();
        if (ev.status === "failed") onFailed(ev.error || "Ingestion failed.");
      },
      ctrl.signal,
    ).catch(() => {
      /* aborted on unmount */
    });
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatId]);

  const done = new Set(state.stages_done || []);

  return (
    <div className="ingest">
      <h2>Preparing your clip…</h2>
      <ol className="stepper">
        {STAGES.map(([key, label]) => {
          const isDone = done.has(key);
          const isActive = state.stage === key && !isDone;
          const cls = isDone ? "done" : isActive ? "active" : "todo";
          return (
            <li key={key} className={cls}>
              <span className="step-mark">{isDone ? "✓" : isActive ? "…" : "○"}</span>
              {label}
            </li>
          );
        })}
      </ol>
      <p className="ingest-note">
        This downloads the clip, transcribes it, and builds a searchable index.
        It can take a couple of minutes.
      </p>
    </div>
  );
}
