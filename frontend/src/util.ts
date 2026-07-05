const YOUTUBE_HOSTS = ["youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be"];

export function isYouTubeUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    return YOUTUBE_HOSTS.includes(parsed.host);
  } catch {
    return false;
  }
}

export function isTimestamp(value: string): boolean {
  const match = /^(\d+):([0-5]?\d):([0-5]?\d)$/.exec(value.trim());
  return match !== null;
}

function toSeconds(value: string): number {
  const [h, m, s] = value.split(":").map(Number);
  return h * 3600 + m * 60 + s;
}

export function isValidRange(start: string, end: string): boolean {
  if (!isTimestamp(start) || !isTimestamp(end)) return false;
  return toSeconds(start) < toSeconds(end);
}

// "00:01:45,140" -> "00:01:45"
export function shortTime(value: string): string {
  return value.split(",")[0];
}
