import type { AxiosError } from "axios";

/** The backend's own explanation for a failed request (FastAPI puts it in
 * `detail`), so a toast can say "Post must be approved first" instead of a
 * generic "request failed". Falls back to `fallback` for network errors or
 * responses with no detail. */
export function serverErrorDetail(err: unknown, fallback: string): string {
  return (err as AxiosError<{ detail?: string }>).response?.data?.detail || fallback;
}
