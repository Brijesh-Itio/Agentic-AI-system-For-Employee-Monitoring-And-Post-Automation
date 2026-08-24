import { useEffect, useState, type ImgHTMLAttributes } from "react";
import { api } from "@/api";

interface AuthImageProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, "src"> {
  /** Path relative to the API base, e.g. "/api/screenshots/file/x.jpg" —
   * fetched through the shared `api` axios instance so the bearer token
   * goes along with it. A plain <img src="..."> can't carry auth headers,
   * which is why screenshots stopped rendering once that endpoint required
   * login: the browser requested them unauthenticated and got a 401. */
  src: string;
}

export default function AuthImage({ src, alt, className, ...rest }: AuthImageProps) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let currentUrl: string | null = null;
    setObjectUrl(null);
    setFailed(false);

    api
      .get(src, { responseType: "blob" })
      .then((res) => {
        if (cancelled) return;
        currentUrl = URL.createObjectURL(res.data as Blob);
        setObjectUrl(currentUrl);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
      if (currentUrl) URL.revokeObjectURL(currentUrl);
    };
  }, [src]);

  if (!objectUrl) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 text-theme-xs text-gray-400 dark:bg-white/5 ${className ?? ""}`}
      >
        {failed ? "Failed to load" : ""}
      </div>
    );
  }

  return <img src={objectUrl} alt={alt} className={className} {...rest} />;
}
