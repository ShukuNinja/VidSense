export interface User {
  id: number;
  email: string;
}

export type ChatStatus = "pending" | "ingesting" | "ready" | "failed";

export interface Chat {
  id: number;
  title: string;
  source_url: string;
  start_time: string;
  end_time: string;
  video_title: string | null;
  status: ChatStatus;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  region_id: number;
  start_time: string;
  end_time: string;
  timestamp?: string; // absolute position in the original video (HH:MM:SS)
  youtube_url?: string | null;
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  is_followup: boolean | null;
  citations: Citation[] | null;
  created_at: string;
}

export interface ChatDetail extends Chat {
  messages: Message[];
}

export interface IngestState {
  status: string; // ingesting | ready | failed
  stage: string | null;
  stages_done?: string[];
  title?: string | null;
  error?: string | null;
}

export type StreamEvent =
  | { type: "meta"; is_followup: boolean; search_query: string }
  | { type: "token"; text: string }
  | { type: "done"; answer: string; is_followup: boolean; citations: Citation[] }
  | { type: "saved"; message_id: number }
  | { type: "error"; message: string };
