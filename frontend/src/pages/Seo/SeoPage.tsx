import { Fragment, FormEvent, ReactElement, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUp,
  Award,
  BarChart3,
  CaseSensitive,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  File,
  FileText,
  Folder,
  Hash,
  Gauge,
  Globe,
  History,
  LayoutDashboard,
  Link2,
  Loader2,
  Mail,
  Pencil,
  Plus,
  Regex,
  RefreshCw,
  Replace,
  ReplaceAll,
  RotateCcw,
  Search,
  Send,
  Server,
  Share2,
  Sparkles,
  Trash2,
  TrendingUp,
  WholeWord,
  X,
  XCircle,
} from "lucide-react";
import type { AxiosError } from "axios";
import DOMPurify from "dompurify";

import PageMeta from "@/components/common/PageMeta";
import RichTextEditor from "@/components/Reports/RichTextEditor";
import { Button } from "@/components/shadcn/button";
import { Card, CardContent } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import StatCard from "@/components/dashboard/StatCard";
import StatusChip from "@/components/dashboard/StatusChip";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import CodeMirror, { ReactCodeMirrorRef } from "@uiw/react-codemirror";
import { php } from "@codemirror/lang-php";
import { html } from "@codemirror/lang-html";
import { search, SearchQuery, setSearchQuery, findNext, findPrevious, replaceNext, replaceAll as cmReplaceAll } from "@codemirror/search";
import { EditorView, keymap } from "@codemirror/view";
import { linter, lintGutter, Diagnostic } from "@codemirror/lint";
import { syntaxTree } from "@codemirror/language";
import { useTheme } from "@/context/ThemeContext";
import { useToast } from "@/context/ToastContext";
import {
  applyTechnicalIssueFix,
  approveBlogPost,
  BlogPost,
  approveSocialPost,
  approveTechnicalIssue,
  BacklinkMention,
  checkPageSpeed,
  createSeoSite,
  draftOutreachEmail,
  Ga4PageRow,
  generateBlogPost,
  generateSeoDigest,
  generateSocialPosts,
  generateTechnicalIssueFix,
  getBacklinks,
  getBlogPosts,
  getGa4Pages,
  getGscQueries,
  getIndexingSubmissions,
  getIndexStatusList,
  getPageSpeedOpportunities,
  getPageSpeedResults,
  getSeoDigests,
  checkSemrushMetrics,
  createServerFileBackup,
  deleteServerFile,
  getSemrushBacklinkGap,
  getSemrushBacklinks,
  getSemrushMetrics,
  getSemrushReferringDomains,
  getSeoJobs,
  getSeoSites,
  getSocialPosts,
  getServerFileBackup,
  getSshStatus,
  listServerDir,
  listServerFileBackups,
  readServerFile,
  renameServerFile,
  restoreServerFileBackup,
  SemrushBacklinkRow,
  SemrushGapRow,
  SemrushReferringDomainRow,
  ServerDirEntry,
  writeServerFile,
  getTechnicalIssues,
  GscQueryRow,
  IndexingNotificationType,
  inspectUrl,
  PageSpeedResult,
  PageSpeedStrategy,
  publishBlogPost,
  publishSocialPost,
  pullBacklinks,
  rejectBlogPost,
  updateBlogPost,
  rejectSocialPost,
  rejectTechnicalIssue,
  REMEDIABLE_RULES,
  runTechnicalAudit,
  SeoJobRun,
  SeoSite,
  SocialPlatform,
  StructureIssue,
  submitForIndexing,
  TechnicalIssue,
  updateSeoSiteCmsConfig,
  updateSeoSiteGoogleConfig,
  updateSeoSiteSshConfig,
} from "@/api";

type Tab = "overview" | "performance" | "indexing" | "social" | "blog" | "backlinks";
type IssueFilter = "pending" | "approved" | "rejected" | "all";

// lucide-react 1.x dropped every brand/logo icon (trademark policy), so
// these platform glyphs are small bespoke SVGs — simplified marks, not
// wordmark reproductions, sized to drop into the same 16/24px icon slots
// as any lucide icon (stroke="currentColor" the exception; these are
// solid fills, matching how a brand mark reads at this size).
function LinkedinIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9h4v12H3V9Zm6 0h3.8v1.71h.05C13.3 9.6 14.6 9 16.2 9c3.2 0 4.8 2.05 4.8 5.6V21h-4v-5.7c0-1.36-.25-2.7-1.95-2.7-1.7 0-2.05 1.3-2.05 2.65V21H9V9Z" />
    </svg>
  );
}

function TwitterIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M18.9 3h3.3l-7.2 8.2L23.5 21h-6.8l-5.3-6.9L5 21H1.7l7.7-8.8L1 3h6.9l4.8 6.3L18.9 3Zm-2.4 16.2h1.8L7.6 4.7H5.7l10.8 14.5Z" />
    </svg>
  );
}

function InstagramIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.2" cy="6.8" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function FacebookIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M13.5 21v-7.5h2.5l.5-3h-3V8.2c0-.87.24-1.46 1.5-1.46H16.5V4.1C16 4.04 14.9 3.94 13.6 3.94c-2.6 0-4.4 1.58-4.4 4.5V10.5H6.7v3H9.2V21h4.3Z" />
    </svg>
  );
}

const severityVariant: Record<TechnicalIssue["severity"], "destructive" | "warning" | "outline"> = {
  critical: "destructive",
  warning: "warning",
  info: "outline",
};

const issueStatusVariant: Record<TechnicalIssue["status"], "warning" | "success" | "outline"> = {
  pending: "warning",
  approved: "success",
  rejected: "outline",
};

const socialStatusVariant: Record<string, "warning" | "success" | "outline" | "destructive"> = {
  draft: "outline",
  approved: "warning",
  posted: "success",
  rejected: "outline",
  failed: "destructive",
};

const ALL_PLATFORMS: SocialPlatform[] = ["linkedin", "twitter", "instagram", "facebook"];

const PLATFORM_ICONS: Record<SocialPlatform, (props: { className?: string }) => ReactElement> = {
  linkedin: LinkedinIcon,
  twitter: TwitterIcon,
  instagram: InstagramIcon,
  facebook: FacebookIcon,
};

const TABS: { id: Tab; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "performance", label: "Performance", icon: Gauge },
  { id: "indexing", label: "Indexing", icon: Search },
  { id: "social", label: "Social", icon: Share2 },
  { id: "blog", label: "Blog", icon: FileText },
  { id: "backlinks", label: "Backlinks", icon: Link2 },
];

const jobStatusVariant: Record<string, "warning" | "success" | "outline" | "destructive"> = {
  running: "warning",
  success: "success",
  failed: "destructive",
};

function formatJobType(jobType: string) {
  return jobType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const blogStatusVariant: Record<string, "warning" | "success" | "outline" | "destructive"> = {
  draft: "outline",
  approved: "warning",
  published: "success",
  rejected: "outline",
  failed: "destructive",
};

// AI-drafted content, same graceful-but-unsanitized-by-default rendering
// risk TaskLog.tsx's sanitizeHtml already guards against for DAR entries —
// this preview should never render anything the CMS wouldn't recognize
// as body content anyway (see ai/seo/blog_content.py's own prompt).
function sanitizeBlogHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ["h1", "h2", "h3", "p", "br", "strong", "em", "ul", "ol", "li", "a"],
    ALLOWED_ATTR: ["href", "rel", "target"],
  });
}

function NewSiteForm({ onCreated, onCancel }: { onCreated: (site: SeoSite) => void; onCancel?: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");

  const createMutation = useMutation({
    mutationFn: () => createSeoSite({ name: name.trim(), base_url: baseUrl.trim(), cms_type: "wordpress" }),
    onSuccess: (site) => {
      queryClient.invalidateQueries({ queryKey: ["seo", "sites"] });
      onCreated(site);
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Could not add this site.");
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !baseUrl.trim()) return;
    createMutation.mutate();
  };

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Globe className="h-4 w-4 text-brand-500" />
          Register a site
        </h2>
        <p className="mb-5 text-theme-sm text-gray-500 dark:text-gray-400">
          Add another site this agent should monitor — internal/private URLs are rejected automatically. Search
          Console / Analytics access for it can be added afterward from the Overview tab.
        </p>
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="site-name">Name</Label>
            <Input id="site-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="WorkPulse AI" />
          </div>
          <div>
            <Label htmlFor="site-url">Base URL</Label>
            <Input
              id="site-url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://workpulse.ai"
            />
          </div>
          <div className="flex gap-2 sm:col-span-2">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Add site
            </Button>
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function GoogleConfigCard({ site }: { site: SeoSite }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [gscSiteUrl, setGscSiteUrl] = useState(site.gsc_site_url ?? "");
  const [ga4PropertyId, setGa4PropertyId] = useState(site.ga4_property_id ?? "");

  useEffect(() => {
    setGscSiteUrl(site.gsc_site_url ?? "");
    setGa4PropertyId(site.ga4_property_id ?? "");
  }, [site.id, site.gsc_site_url, site.ga4_property_id]);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateSeoSiteGoogleConfig(site.id, {
        gsc_site_url: gscSiteUrl.trim(),
        ga4_property_id: ga4PropertyId.trim(),
      }),
    onSuccess: () => {
      toast.success("Google Search Console / Analytics config saved for this site.");
      queryClient.invalidateQueries({ queryKey: ["seo", "sites"] });
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Could not save this site's Google config.");
    },
  });

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Search className="h-4 w-4 text-brand-500" />
          Google Search Console & Analytics
        </h2>
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          Per-site override — set the verified Search Console property and GA4 property this site uses, so checking
          a different website never requires editing .env or restarting the backend. Leave blank to fall back to the
          GSC_SITE_URL / GA4_PROPERTY_ID configured there. The service account still needs to be granted access to a
          new property in Search Console/Analytics itself before this will work for it.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="gsc-site-url">Search Console property (site URL)</Label>
            <Input
              id="gsc-site-url"
              value={gscSiteUrl}
              onChange={(e) => setGscSiteUrl(e.target.value)}
              placeholder={site.base_url}
            />
          </div>
          <div>
            <Label htmlFor="ga4-property-id">GA4 property ID</Label>
            <Input
              id="ga4-property-id"
              value={ga4PropertyId}
              onChange={(e) => setGa4PropertyId(e.target.value)}
              placeholder="properties/123456789"
            />
          </div>
        </div>
        <Button className="mt-4" size="sm" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Save
        </Button>
      </CardContent>
    </Card>
  );
}

function CmsConfigCard({ site }: { site: SeoSite }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [cmsBaseUrl, setCmsBaseUrl] = useState(site.cms_base_url ?? "");
  const [username, setUsername] = useState(site.cms_username ?? "");
  const [appPassword, setAppPassword] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [collectionId, setCollectionId] = useState(site.cms_collection_id ?? "");

  useEffect(() => {
    setCmsBaseUrl(site.cms_base_url ?? "");
    setUsername(site.cms_username ?? "");
    setAppPassword("");
    setApiToken("");
    setCollectionId(site.cms_collection_id ?? "");
  }, [site.id, site.cms_base_url, site.cms_username, site.cms_collection_id]);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateSeoSiteCmsConfig(site.id, {
        cms_base_url: cmsBaseUrl.trim(),
        cms_username: username.trim(),
        cms_app_password: appPassword.trim(),
        cms_api_token: apiToken.trim(),
        cms_collection_id: collectionId.trim(),
      }),
    onSuccess: () => {
      toast.success("CMS publishing config saved for this site.");
      queryClient.invalidateQueries({ queryKey: ["seo", "sites"] });
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Could not save this site's CMS config.");
    },
  });

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Globe className="h-4 w-4 text-brand-500" />
          CMS Publishing
        </h2>
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          Per-site override — where the Blog tab's "Publish" action creates a draft, and where Backlinks' outreach
          content ends up updated. Leave blank to fall back to WORDPRESS_*/WEBFLOW_* in .env. Password/token fields
          show blank even when one is already saved — leave them blank to keep the saved value, type a new one to
          replace it.
        </p>
        {site.cms_type === "wordpress" ? (
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <Label htmlFor="cms-base-url">WordPress site URL</Label>
              <Input
                id="cms-base-url"
                value={cmsBaseUrl}
                onChange={(e) => setCmsBaseUrl(e.target.value)}
                placeholder={site.base_url}
              />
            </div>
            <div>
              <Label htmlFor="cms-username">Username</Label>
              <Input id="cms-username" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="cms-app-password">Application password{site.cms_app_password_set ? " (saved)" : ""}</Label>
              <Input
                id="cms-app-password"
                type="password"
                value={appPassword}
                onChange={(e) => setAppPassword(e.target.value)}
                placeholder={site.cms_app_password_set ? "•••••••• (leave blank to keep)" : ""}
              />
            </div>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="cms-api-token">Webflow API token{site.cms_api_token_set ? " (saved)" : ""}</Label>
              <Input
                id="cms-api-token"
                type="password"
                value={apiToken}
                onChange={(e) => setApiToken(e.target.value)}
                placeholder={site.cms_api_token_set ? "•••••••• (leave blank to keep)" : ""}
              />
            </div>
            <div>
              <Label htmlFor="cms-collection-id">Collection ID</Label>
              <Input id="cms-collection-id" value={collectionId} onChange={(e) => setCollectionId(e.target.value)} />
            </div>
          </div>
        )}
        <Button className="mt-4" size="sm" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Save
        </Button>
      </CardContent>
    </Card>
  );
}

const SERVER_PROTOCOLS = [
  { value: "sftp", label: "SFTP (SSH)", defaultPort: "22" },
  { value: "ftp", label: "FTP", defaultPort: "21" },
  { value: "ftps", label: "FTPS (Explicit)", defaultPort: "21" },
] as const;

function ServerAccessConfigCard({ site }: { site: SeoSite }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [sshHost, setSshHost] = useState(site.ssh_host ?? "");
  const [sshPort, setSshPort] = useState(site.ssh_port ?? "");
  const [sshUsername, setSshUsername] = useState(site.ssh_username ?? "");
  const [sshProtocol, setSshProtocol] = useState(site.ssh_protocol ?? "sftp");
  const [sshPassword, setSshPassword] = useState("");

  useEffect(() => {
    setSshHost(site.ssh_host ?? "");
    setSshPort(site.ssh_port ?? "");
    setSshUsername(site.ssh_username ?? "");
    setSshProtocol(site.ssh_protocol ?? "sftp");
    setSshPassword("");
  }, [site.id, site.ssh_host, site.ssh_port, site.ssh_username, site.ssh_protocol]);

  const protocolMeta = SERVER_PROTOCOLS.find((p) => p.value === sshProtocol) ?? SERVER_PROTOCOLS[0];

  const saveMutation = useMutation({
    mutationFn: () =>
      updateSeoSiteSshConfig(site.id, {
        ssh_host: sshHost.trim(),
        ssh_port: sshPort.trim(),
        ssh_username: sshUsername.trim(),
        ssh_protocol: sshProtocol,
        ssh_password: sshPassword.trim(),
      }),
    onSuccess: () => {
      toast.success("Server access credentials saved for this site.");
      queryClient.invalidateQueries({ queryKey: ["seo", "sites"] });
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Could not save this site's server access credentials.");
    },
  });

  const testMutation = useMutation({
    mutationFn: () => getSshStatus(site.id),
    onSuccess: (result) => {
      if (result.reachable) {
        toast.success(`Connected — ${protocolMeta.label} credentials work.`);
      } else {
        toast.error(result.error || "Could not connect with these credentials.");
      }
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Could not test this site's server connection.");
    },
  });

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Server className="h-4 w-4 text-brand-500" />
          Server Access
        </h2>
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          Direct file-level access to this site's hosting account — for the files CMS Publishing above can't reach,
          like wp-content/mu-plugins/*.php or .htaccess. No .env fallback exists for these; each site needs its own
          credentials. Password shows blank even when one is already saved — leave it blank to keep the saved value.
          Not every host offers SFTP — check your hosting panel if unsure which protocol it actually supports.
        </p>
        <div className="grid gap-4 sm:grid-cols-5">
          <div>
            <Label htmlFor="ssh-protocol">Protocol</Label>
            <select
              id="ssh-protocol"
              value={sshProtocol}
              onChange={(e) => setSshProtocol(e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
            >
              {SERVER_PROTOCOLS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="ssh-host">Server host / IP address</Label>
            <Input id="ssh-host" value={sshHost} onChange={(e) => setSshHost(e.target.value)} placeholder="203.0.113.10" />
          </div>
          <div>
            <Label htmlFor="ssh-port">Port</Label>
            <Input id="ssh-port" value={sshPort} onChange={(e) => setSshPort(e.target.value)} placeholder={protocolMeta.defaultPort} />
          </div>
          <div>
            <Label htmlFor="ssh-username">Username</Label>
            <Input id="ssh-username" value={sshUsername} onChange={(e) => setSshUsername(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="ssh-password">Password{site.ssh_password_set ? " (saved)" : ""}</Label>
            <Input
              id="ssh-password"
              type="password"
              value={sshPassword}
              onChange={(e) => setSshPassword(e.target.value)}
              placeholder={site.ssh_password_set ? "•••••••• (leave blank to keep)" : ""}
            />
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <Button size="sm" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Save
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending || !site.ssh_host}
          >
            {testMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Test Connection
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function joinServerPath(dir: string, name: string): string {
  return dir.endsWith("/") ? `${dir}${name}` : `${dir}/${name}`;
}

function parentServerPath(dir: string): string {
  const trimmed = dir.replace(/\/+$/, "");
  const idx = trimmed.lastIndexOf("/");
  return idx <= 0 ? "/" : trimmed.slice(0, idx);
}

// Only meaningful for a site whose Server Access root is the same as its
// web document root (true for every site this was built/tested against —
// see automation/seo/issue_applier.py's _remote_path_for_url comment for
// the same assumption made server-side). An absolute path always
// resolves against the base URL's origin regardless of the base's own
// path or trailing slash, so this doesn't need to special-case either.
function previewUrlFor(baseUrl: string, path: string): string | null {
  try {
    return new URL(path, baseUrl).href;
  } catch {
    return null;
  }
}

// SQLite's CURRENT_TIMESTAMP (what created_at comes from) is UTC but
// has no timezone marker in the string it produces ("2026-09-09T07:50:05"
// — verified live against a real API response) — appending "Z" is what
// tells JS to parse it as UTC instead of local time, which it would
// otherwise silently misinterpret as being off by the viewer's own UTC
// offset.
function formatUtcTimestamp(value: string | null): string {
  if (!value) return "unknown time";
  const date = new Date(value.endsWith("Z") ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function serverErrorDetail(err: unknown, fallback: string): string {
  return (err as AxiosError<{ detail?: string }>).response?.data?.detail || fallback;
}

// Only meaningful for .html/.htm — a .php file's real output only
// exists once a server actually executes it; rendering raw PHP source
// in a browser tab would just show the unexecuted tags as inert text,
// not a preview of anything real.
function isPreviewableAsHtml(path: string): boolean {
  const lower = path.toLowerCase();
  return lower.endsWith(".html") || lower.endsWith(".htm");
}

// Renders `html` directly in a new tab — the CURRENT content, unsaved
// changes included, without ever touching the live site. A <base> tag
// is injected so the page's own relative CSS/JS/image links still
// resolve against the real site (this document has no URL of its own —
// window.open("", "_blank") — so without it every asset link would be
// broken). A small fixed banner marks it clearly as a preview, the same
// idea as Blogger's own "Preview" watermark, since nothing else here
// distinguishes it from the real page.
function openUnsavedHtmlPreview(html: string, baseUrl: string): void {
  let origin = "";
  try {
    origin = new URL(baseUrl).origin;
  } catch {
    // no usable origin — asset links just won't resolve, not fatal
  }
  const baseTag = origin ? `<base href="${origin}/">` : "";
  const banner =
    '<div style="position:fixed;top:0;left:0;right:0;z-index:2147483647;' +
    "background:#4f46e5;color:#fff;text-align:center;padding:6px 12px;" +
    'font:600 13px -apple-system,system-ui,sans-serif;">' +
    "PREVIEW — unsaved changes, not the live page</div>";

  let output = html;
  output = /<head[^>]*>/i.test(output)
    ? output.replace(/<head[^>]*>/i, (m) => `${m}${baseTag}`)
    : baseTag + output;
  output = /<body[^>]*>/i.test(output)
    ? output.replace(/<body[^>]*>/i, (m) => `${m}${banner}`)
    : banner + output;

  const win = window.open("", "_blank");
  if (!win) return;
  win.document.open();
  win.document.write(output);
  win.document.close();
}


// Generic across any Lezer-parsed language (works for both PHP and HTML
// modes below unchanged): the parser marks a node as an error whenever it
// couldn't cleanly make sense of the surrounding structure — an unclosed
// tag, a mismatched closing tag, a broken attribute — which is exactly
// what CodeMirror's own official linting example uses for this. No
// separate validator library needed.
function syntaxErrorLinter(view: EditorView): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];
  syntaxTree(view.state).iterate({
    enter: (node) => {
      if (node.type.isError) {
        diagnostics.push({
          from: node.from,
          to: node.to > node.from ? node.to : Math.min(node.from + 1, view.state.doc.length),
          severity: "error",
          message: "Syntax error — check for an unclosed or mismatched tag nearby.",
        });
      }
    },
  });
  return diagnostics;
}

function codeMirrorExtensionsFor(path: string) {
  const lower = path.toLowerCase();
  if (lower.endsWith(".php")) return [php(), linter(syntaxErrorLinter)];
  if (lower.endsWith(".html") || lower.endsWith(".htm")) return [html(), linter(syntaxErrorLinter)];
  return [];
}

interface CodeEditorSearchBarProps {
  editorRef: React.RefObject<ReactCodeMirrorRef | null>;
  onClose: () => void;
}

function CodeEditorSearchBar({ editorRef, onClose }: CodeEditorSearchBarProps) {
  const [query, setQuery] = useState("");
  const [replacement, setReplacement] = useState("");
  const [matchCase, setMatchCase] = useState(false);
  const [useRegex, setUseRegex] = useState(false);
  const [wholeWord, setWholeWord] = useState(false);

  useEffect(() => {
    const view = editorRef.current?.view;
    if (!view) return;
    view.dispatch({
      effects: setSearchQuery.of(
        new SearchQuery({ search: query, replace: replacement, caseSensitive: matchCase, regexp: useRegex, wholeWord })
      ),
    });
  }, [editorRef, query, replacement, matchCase, useRegex, wholeWord]);

  const withView = (fn: (view: EditorView) => void) => {
    const view = editorRef.current?.view;
    if (view) fn(view);
  };

  const toggles = [
    { key: "matchCase", label: "Match case", Icon: CaseSensitive, value: matchCase, set: setMatchCase },
    { key: "wholeWord", label: "Whole word", Icon: WholeWord, value: wholeWord, set: setWholeWord },
    { key: "useRegex", label: "Regular expression", Icon: Regex, value: useRegex, set: setUseRegex },
  ] as const;

  return (
    <div className="absolute right-3 top-3 z-10 w-80 rounded-xl border border-gray-200 bg-white p-3 shadow-lg dark:border-gray-700 dark:bg-gray-900">
      <div className="flex items-center gap-1.5">
        <Search className="h-3.5 w-3.5 shrink-0 text-gray-400" />
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") withView((v) => (e.shiftKey ? findPrevious(v) : findNext(v)));
            if (e.key === "Escape") onClose();
          }}
          placeholder="Find"
          className="h-7 flex-1 rounded-md border border-gray-200 bg-transparent px-2 text-theme-xs text-gray-800 focus:border-brand-300 focus:outline-hidden focus:ring-2 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
        />
        <button
          type="button"
          onClick={() => withView(findPrevious)}
          title="Previous match (Shift+Enter)"
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-white/5 dark:hover:text-gray-200"
        >
          <ChevronUp className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => withView(findNext)}
          title="Next match (Enter)"
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-white/5 dark:hover:text-gray-200"
        >
          <ChevronDown className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={onClose}
          title="Close (Esc)"
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-white/5 dark:hover:text-gray-200"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="mt-2 flex items-center gap-1.5">
        <Replace className="h-3.5 w-3.5 shrink-0 text-gray-400" />
        <input
          value={replacement}
          onChange={(e) => setReplacement(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && withView(replaceNext)}
          placeholder="Replace"
          className="h-7 flex-1 rounded-md border border-gray-200 bg-transparent px-2 text-theme-xs text-gray-800 focus:border-brand-300 focus:outline-hidden focus:ring-2 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
        />
        <button
          type="button"
          onClick={() => withView(replaceNext)}
          title="Replace"
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-white/5 dark:hover:text-gray-200"
        >
          <Replace className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => withView(cmReplaceAll)}
          title="Replace all"
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-white/5 dark:hover:text-gray-200"
        >
          <ReplaceAll className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="mt-2 flex items-center gap-1 border-t border-gray-100 pt-2 dark:border-gray-800">
        {toggles.map(({ key, label, Icon, value, set }) => (
          <button
            key={key}
            type="button"
            title={label}
            onClick={() => set(!value)}
            className={`rounded p-1 ${
              value
                ? "bg-brand-50 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400"
                : "text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
          </button>
        ))}
      </div>
    </div>
  );
}

const BACKUP_ACTION_LABELS: Record<string, string> = {
  write: "Saved",
  "edit-start": "Edit started",
  rename: "Renamed",
  delete: "Deleted",
};

function ServerFileHistoryPanel({
  siteId,
  path,
  currentlyOpenPath,
  onRestored,
}: {
  siteId: number;
  path: string;
  currentlyOpenPath: string | null;
  onRestored: (content: string) => void;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [viewingId, setViewingId] = useState<number | null>(null);
  const backupsQueryKey = ["seo", "server-backups", siteId, path];
  const backupsQuery = useQuery({
    queryKey: backupsQueryKey,
    queryFn: () => listServerFileBackups(siteId, path),
  });

  const viewQuery = useQuery({
    queryKey: ["seo", "server-backup-content", viewingId],
    queryFn: () => getServerFileBackup(viewingId as number),
    enabled: viewingId !== null,
  });

  const restoreMutation = useMutation({
    mutationFn: (backupId: number) => restoreServerFileBackup(backupId),
    onSuccess: (result) => {
      toast.success("Restored — the previous content is now saved on the server.");
      queryClient.invalidateQueries({ queryKey: backupsQueryKey });
      if (currentlyOpenPath === result.path) onRestored(result.content);
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Could not restore this backup.")),
  });

  const backups = backupsQuery.data ?? [];

  return (
    <div className="mb-3 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-white/5">
      <p className="mb-2 text-theme-xs font-medium text-gray-500 dark:text-gray-400">
        Backup history for {path} — kept for 15 days
      </p>
      {backupsQuery.isLoading ? (
        <div className="flex h-12 items-center justify-center text-gray-400">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      ) : backups.length === 0 ? (
        <p className="text-theme-xs text-gray-400">No changes recorded yet for this file.</p>
      ) : (
        <ul className="space-y-1.5">
          {backups.map((b) => (
            <li key={b.id} className="text-theme-xs">
              <div className="flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => setViewingId(viewingId === b.id ? null : b.id)}
                  className="text-left text-gray-600 hover:text-brand-500 dark:text-gray-300"
                >
                  <span className="font-medium">{BACKUP_ACTION_LABELS[b.action] ?? b.action}</span>
                  {b.action === "rename" && b.new_path && <> → {b.new_path}</>}
                  {" — "}
                  {formatUtcTimestamp(b.created_at)}
                </button>
                <div className="flex shrink-0 gap-1.5">
                  <Button size="sm" variant="outline" onClick={() => setViewingId(viewingId === b.id ? null : b.id)}>
                    {viewingId === b.id ? "Hide" : "View"}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      if (window.confirm(`Restore the content as it was at "${BACKUP_ACTION_LABELS[b.action] ?? b.action}"?`)) {
                        restoreMutation.mutate(b.id);
                      }
                    }}
                    disabled={restoreMutation.isPending}
                  >
                    <RotateCcw className="h-3 w-3" />
                    Restore
                  </Button>
                </div>
              </div>
              {viewingId === b.id && (
                <div className="mt-1.5 max-h-48 overflow-auto rounded-md border border-gray-200 bg-white p-2 font-mono text-theme-xs text-gray-700 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300">
                  {viewQuery.isLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : viewQuery.data?.content ? (
                    <pre className="whitespace-pre-wrap break-all">{viewQuery.data.content}</pre>
                  ) : (
                    <span className="text-gray-400">No content stored for this entry.</span>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ServerFileBrowser({ site }: { site: SeoSite }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { theme } = useTheme();
  const [path, setPath] = useState("/");
  const [pathInput, setPathInput] = useState("/");
  const [openFile, setOpenFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const editorRef = useRef<ReactCodeMirrorRef>(null);
  // The file's content as it was when opened — kept separate from
  // fileContent (which changes on every keystroke) so the backup can
  // save the ORIGINAL, not whatever's been typed so far.
  const originalContentRef = useRef<string>("");
  // Per-open-file, not per-keystroke: true once the first real edit on
  // this file has saved its one backup. Merely opening a file —
  // including an accidental click on the wrong one — never creates a
  // backup; only an actual change does.
  const hasBackedUpRef = useRef(false);

  const closeSearch = () => {
    setSearchOpen(false);
    const view = editorRef.current?.view;
    if (view) view.dispatch({ effects: setSearchQuery.of(new SearchQuery({ search: "" })) });
  };

  // Recreating this array on every render (e.g. every keystroke, since
  // fileContent changes) would make @uiw/react-codemirror reconfigure the
  // editor each time and disrupt cursor position — memoized so it's only
  // rebuilt when the open file actually changes.
  const editorExtensions = useMemo(
    () => [
      EditorView.lineWrapping,
      lintGutter(),
      search(),
      keymap.of([
        {
          key: "Mod-f",
          run: () => {
            setSearchOpen(true);
            return true;
          },
          preventDefault: true,
        },
        {
          key: "Mod-h",
          run: () => {
            setSearchOpen(true);
            return true;
          },
          preventDefault: true,
        },
      ]),
      ...(openFile ? codeMirrorExtensionsFor(openFile) : []),
    ],
    [openFile]
  );

  const listQueryKey = ["seo", "server-list", site.id, path];
  const listQuery = useQuery({
    queryKey: listQueryKey,
    queryFn: () => listServerDir(site.id, path),
    enabled: Boolean(site.ssh_host),
    retry: false,
  });

  const goTo = (next: string) => {
    setPath(next);
    setPathInput(next);
    setOpenFile(null);
  };

  // Opening a file just loads it — no download yet. The backup only
  // fires on the first real edit (see handleContentChange below), so an
  // accidental click on the wrong file never produces an unwanted
  // download.
  const openFileForEditing = (filePath: string, content: string) => {
    setOpenFile(filePath);
    setFileContent(content);
    originalContentRef.current = content;
    hasBackedUpRef.current = false;
  };

  const editStartBackupMutation = useMutation({
    mutationFn: (content: string) => createServerFileBackup(site.id, openFile as string, content),
    onSuccess: () => {
      toast.success("Backup saved to history.");
      queryClient.invalidateQueries({ queryKey: ["seo", "server-backups", site.id, openFile] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Could not save a backup of this file.")),
  });

  // The single trigger point for the backup: the first character
  // actually changed since this file was opened (or last restored).
  // Compares against originalContentRef, not the previous fileContent,
  // so it only fires once per edit session — not on every keystroke —
  // and backs up the ORIGINAL content, the "old things" that would
  // otherwise be lost, not whatever's been typed so far.
  const handleContentChange = (value: string) => {
    setFileContent(value);
    if (!hasBackedUpRef.current && openFile && value !== originalContentRef.current) {
      hasBackedUpRef.current = true;
      editStartBackupMutation.mutate(originalContentRef.current);
    }
  };

  const readMutation = useMutation({
    mutationFn: (filePath: string) => readServerFile(site.id, filePath),
    onSuccess: (result) => openFileForEditing(result.path, result.content),
    onError: (err) => toast.error(serverErrorDetail(err, "Could not read this file.")),
  });

  // "Go" doesn't know upfront whether what you typed is a directory or a
  // file — if listing it fails (a real, expected server response for a
  // file path, not a bug), fall back to opening it as a file instead of
  // just surfacing the raw "can't list a file" error.
  const goMutation = useMutation({
    mutationFn: async (rawPath: string) => {
      const targetPath = rawPath.trim() || "/";
      try {
        const listing = await listServerDir(site.id, targetPath);
        return { kind: "dir" as const, dirPath: targetPath, listing };
      } catch {
        const parent = parentServerPath(targetPath);
        const [listing, file] = await Promise.all([listServerDir(site.id, parent), readServerFile(site.id, targetPath)]);
        return { kind: "file" as const, dirPath: parent, listing, file };
      }
    },
    onSuccess: (result) => {
      setPath(result.dirPath);
      setPathInput(result.dirPath);
      queryClient.setQueryData(["seo", "server-list", site.id, result.dirPath], result.listing);
      if (result.kind === "file") {
        openFileForEditing(result.file.path, result.file.content);
      } else {
        setOpenFile(null);
      }
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Could not open this path as a directory or a file.")),
  });

  const saveMutation = useMutation({
    mutationFn: () => writeServerFile(site.id, openFile as string, fileContent),
    onSuccess: () => toast.success(`Saved ${openFile}`),
    onError: (err) => toast.error(serverErrorDetail(err, "Could not save this file.")),
  });

  const renameMutation = useMutation({
    mutationFn: ({ oldPath, newPath }: { oldPath: string; newPath: string }) =>
      renameServerFile(site.id, oldPath, newPath),
    onSuccess: (_data, { oldPath }) => {
      toast.success("Renamed.");
      if (openFile === oldPath) setOpenFile(null);
      queryClient.invalidateQueries({ queryKey: listQueryKey });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Could not rename this file.")),
  });

  const deleteMutation = useMutation({
    mutationFn: (filePath: string) => deleteServerFile(site.id, filePath),
    onSuccess: (_data, filePath) => {
      toast.success("Deleted.");
      if (openFile === filePath) setOpenFile(null);
      queryClient.invalidateQueries({ queryKey: listQueryKey });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Could not delete this file.")),
  });

  // Previewing a row you haven't opened for editing yet — reads the
  // file fresh (no unsaved local edits exist for it) and renders that,
  // same client-side approach as the open editor's own Preview button,
  // still never touching the live URL.
  const rowPreviewMutation = useMutation({
    mutationFn: (filePath: string) => readServerFile(site.id, filePath),
    onSuccess: (result) => openUnsavedHtmlPreview(result.content, site.base_url),
    onError: (err) => toast.error(serverErrorDetail(err, "Could not load this file to preview it.")),
  });

  const handleEntryClick = (entry: ServerDirEntry) => {
    const entryPath = joinServerPath(path, entry.name);
    if (entry.is_dir) {
      goTo(entryPath);
    } else {
      readMutation.mutate(entryPath);
    }
  };

  const handleRename = (entry: ServerDirEntry) => {
    const newName = window.prompt(`Rename "${entry.name}" to:`, entry.name);
    if (!newName || newName === entry.name) return;
    renameMutation.mutate({ oldPath: joinServerPath(path, entry.name), newPath: joinServerPath(path, newName) });
  };

  const handleDelete = (entry: ServerDirEntry) => {
    if (entry.is_dir) {
      toast.error("This browser only deletes files, not directories.");
      return;
    }
    if (!window.confirm(`Delete "${entry.name}"? This cannot be undone.`)) return;
    deleteMutation.mutate(joinServerPath(path, entry.name));
  };

  if (!site.ssh_host) {
    return null;
  }

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Folder className="h-4 w-4 text-brand-500" />
          Server Files
        </h2>
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          Browse this site's hosting filesystem over the Server Access credentials above (SFTP, FTP, or FTPS). Click a
          folder to open it, a file to view/edit it. Typical WordPress paths: public_html/wp-content/mu-plugins,
          public_html/.htaccess.
        </p>

        <form
          className="mb-3 flex gap-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            goMutation.mutate(pathInput);
          }}
        >
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => goTo(parentServerPath(path))}
            disabled={path === "/"}
          >
            <ArrowUp className="h-4 w-4" />
          </Button>
          <Input value={pathInput} onChange={(e) => setPathInput(e.target.value)} className="flex-1" />
          <Button type="submit" size="sm" variant="outline" disabled={goMutation.isPending}>
            {goMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Go"}
          </Button>
        </form>

        {listQuery.isError ? (
          <p className="text-theme-sm text-error-500">{serverErrorDetail(listQuery.error, "Could not list this directory.")}</p>
        ) : (
          <div className="max-h-64 overflow-y-auto rounded-lg border border-gray-200 dark:border-gray-800">
            {(listQuery.data?.entries ?? []).map((entry) => (
              <div
                key={entry.name}
                className="flex items-center justify-between gap-2 border-b border-gray-100 px-3 py-2 text-theme-sm last:border-b-0 dark:border-gray-800"
              >
                <button
                  type="button"
                  onClick={() => handleEntryClick(entry)}
                  className="flex flex-1 items-center gap-2 text-left text-gray-700 hover:text-brand-500 dark:text-gray-300"
                >
                  {entry.is_dir ? <Folder className="h-4 w-4 shrink-0" /> : <File className="h-4 w-4 shrink-0" />}
                  <span className="truncate">{entry.name}</span>
                </button>
                <div className="flex shrink-0 gap-1">
                  {!entry.is_dir &&
                    (() => {
                      const entryPath = joinServerPath(path, entry.name);
                      if (isPreviewableAsHtml(entryPath)) {
                        return (
                          <button
                            type="button"
                            onClick={() => rowPreviewMutation.mutate(entryPath)}
                            className="rounded p-1 text-gray-400 hover:text-brand-500"
                            title="Preview in a new tab (renders the file's real content, not the live URL)"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </button>
                        );
                      }
                      // Not HTML (e.g. .php) — no meaningful way to
                      // render it client-side, so the live URL is the
                      // closest available approximation.
                      const previewUrl = previewUrlFor(site.base_url, entryPath);
                      return (
                        previewUrl && (
                          <a
                            href={previewUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="rounded p-1 text-gray-400 hover:text-brand-500"
                            title="Open the live URL (server-rendered content can't be previewed client-side)"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )
                      );
                    })()}
                  <button
                    type="button"
                    onClick={() => handleRename(entry)}
                    className="rounded p-1 text-gray-400 hover:text-brand-500"
                    title="Rename"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  {!entry.is_dir && (
                    <button
                      type="button"
                      onClick={() => handleDelete(entry)}
                      className="rounded p-1 text-gray-400 hover:text-error-500"
                      title="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
            {listQuery.data && listQuery.data.entries.length === 0 && (
              <p className="px-3 py-4 text-theme-sm text-gray-400">Empty directory.</p>
            )}
          </div>
        )}

        {openFile && (
          <div className="mt-4 border-t border-gray-200 pt-4 dark:border-gray-800">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-theme-sm font-medium text-gray-700 dark:text-gray-300">{openFile}</span>
              <div className="flex gap-2">
                {isPreviewableAsHtml(openFile) ? (
                  <Button
                    size="sm"
                    variant="outline"
                    type="button"
                    onClick={() => openUnsavedHtmlPreview(fileContent, site.base_url)}
                    title="Renders your current edits, unsaved changes included — not the live URL"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Preview
                  </Button>
                ) : (
                  (() => {
                    const previewUrl = previewUrlFor(site.base_url, openFile);
                    return (
                      previewUrl && (
                        <Button size="sm" variant="outline" asChild title="Server-rendered content can't be previewed client-side">
                          <a href={previewUrl} target="_blank" rel="noreferrer">
                            <ExternalLink className="h-3.5 w-3.5" />
                            Preview (live)
                          </a>
                        </Button>
                      )
                    );
                  })()
                )}
                <Button size="sm" variant="outline" type="button" onClick={() => setHistoryOpen((v) => !v)}>
                  <History className="h-3.5 w-3.5" />
                  History
                </Button>
                <Button size="sm" variant="outline" type="button" onClick={() => setSearchOpen((v) => !v)}>
                  <Search className="h-3.5 w-3.5" />
                  Find & Replace
                </Button>
                <Button size="sm" onClick={() => setOpenFile(null)} variant="outline">
                  Close
                </Button>
              </div>
            </div>
            <p className="mb-2 text-theme-xs text-gray-400">Ctrl/Cmd+F to find, Ctrl/Cmd+H to find &amp; replace.</p>
            {historyOpen && (
              <ServerFileHistoryPanel
                siteId={site.id}
                path={openFile}
                currentlyOpenPath={openFile}
                onRestored={(content) => {
                  setFileContent(content);
                  // Restored content becomes the new baseline — the
                  // next edit after this should back up *this* content,
                  // not the pre-restore one.
                  originalContentRef.current = content;
                  hasBackedUpRef.current = false;
                }}
              />
            )}
            <div className="relative">
              <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-800">
                <CodeMirror
                  ref={editorRef}
                  value={fileContent}
                  onChange={handleContentChange}
                  height="420px"
                  theme={theme === "dark" ? "dark" : "light"}
                  basicSetup={{ searchKeymap: false }}
                  extensions={editorExtensions}
                />
              </div>
              {searchOpen && <CodeEditorSearchBar editorRef={editorRef} onClose={closeSearch} />}
            </div>
            <Button className="mt-2" size="sm" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function OverviewTab({ site }: { site: SeoSite }) {
  const siteId = site.id;
  const queryClient = useQueryClient();
  const toast = useToast();
  const [issueFilter, setIssueFilter] = useState<IssueFilter>("pending");

  const digestsQuery = useQuery({ queryKey: ["seo", "digests", siteId], queryFn: () => getSeoDigests(siteId) });
  const latestDigest = digestsQuery.data?.[0] ?? null;

  const issuesQuery = useQuery({
    queryKey: ["seo", "issues", siteId, issueFilter],
    queryFn: () => getTechnicalIssues(siteId, issueFilter === "all" ? undefined : issueFilter),
  });
  const issues = issuesQuery.data ?? [];

  const pendingCountQuery = useQuery({
    queryKey: ["seo", "issues", siteId, "pending-count"],
    queryFn: () => getTechnicalIssues(siteId, "pending"),
  });
  const pendingCount = pendingCountQuery.data?.length ?? 0;

  const pagespeedQuery = useQuery({
    queryKey: ["seo", "pagespeed", siteId, "latest"],
    queryFn: () => getPageSpeedResults(siteId, 1),
  });
  const latestScore = pagespeedQuery.data?.[0]?.performance_score ?? null;

  const jobsQuery = useQuery({ queryKey: ["seo", "jobs", siteId], queryFn: () => getSeoJobs(siteId, 15) });
  const jobs = jobsQuery.data ?? [];
  const today = new Date().toISOString().slice(0, 10);
  const todaysJobs = jobs.filter((j) => j.run_date === today);
  const todaysFailures = todaysJobs.filter((j) => j.status === "failed").length;
  const automationTone: "success" | "warning" | "error" =
    todaysJobs.length === 0 ? "warning" : todaysFailures > 0 ? "error" : "success";
  const automationValue =
    todaysJobs.length === 0
      ? "Not run yet today"
      : todaysFailures > 0
      ? `${todaysFailures} of ${todaysJobs.length} step(s) failed`
      : `${todaysJobs.length} step(s) completed`;

  const auditMutation = useMutation({
    mutationFn: () => runTechnicalAudit(siteId),
    onSuccess: (found) => {
      toast.success(`Audit complete: ${found.length} issue(s) found.`);
      queryClient.invalidateQueries({ queryKey: ["seo", "issues", siteId] });
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Audit failed — see server logs.");
    },
  });

  const digestMutation = useMutation({
    mutationFn: () => generateSeoDigest(siteId),
    onSuccess: () => {
      toast.success("Digest generated.");
      queryClient.invalidateQueries({ queryKey: ["seo", "digests", siteId] });
    },
    onError: () => toast.error("Digest generation failed — check that Ollama is running."),
  });

  const approveMutation = useMutation({
    mutationFn: (issueId: number) => approveTechnicalIssue(issueId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "issues", siteId] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (issueId: number) => rejectTechnicalIssue(issueId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "issues", siteId] }),
  });

  const generateFixMutation = useMutation({
    mutationFn: (issueId: number) => generateTechnicalIssueFix(issueId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "issues", siteId] }),
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Could not generate a fix for this issue.");
    },
  });

  const applyFixMutation = useMutation({
    mutationFn: (issueId: number) => applyTechnicalIssueFix(issueId),
    onSuccess: (result) => {
      if (result.fix_applied) {
        toast.success("Fix applied to the live site.");
      } else {
        toast.error(result.fix_error || "Applying the fix failed.");
      }
      queryClient.invalidateQueries({ queryKey: ["seo", "issues", siteId] });
    },
  });

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Pending Issues"
          value={String(pendingCount)}
          icon={AlertTriangle}
          tone={pendingCount === 0 ? "success" : "warning"}
          hint={pendingCount === 0 ? "All clear" : "Awaiting review"}
          loading={pendingCountQuery.isLoading}
        />
        <StatCard
          label="Latest PageSpeed Score"
          value={latestScore != null ? String(Math.round(latestScore)) : "—"}
          icon={Gauge}
          tone={latestScore == null ? "neutral" : latestScore >= 90 ? "success" : latestScore >= 50 ? "warning" : "error"}
          hint={latestScore == null ? "No check yet" : "Mobile, most recent"}
          loading={pagespeedQuery.isLoading}
        />
        <StatCard
          label="Last Digest"
          value={latestDigest ? latestDigest.run_date : "—"}
          icon={Sparkles}
          tone="neutral"
          hint={latestDigest ? (latestDigest.slack_delivered ? "Sent to Slack" : "Not sent to Slack") : "None generated yet"}
          loading={digestsQuery.isLoading}
        />
        <StatCard
          label="Registered Since"
          value={site.created_at ? site.created_at.slice(0, 10) : "—"}
          icon={Globe}
          tone="neutral"
          hint={site.cms_type === "wordpress" ? "WordPress" : "Webflow"}
        />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <StatusChip
          label="Daily automation"
          value={automationValue}
          icon={History}
          tone={automationTone}
          hint="Runs once a day for every active site — technical audit, GSC, GA4, PageSpeed, digest"
          loading={jobsQuery.isLoading}
        />
      </div>

      <div className="flex flex-wrap gap-3">
        <Button onClick={() => auditMutation.mutate()} disabled={auditMutation.isPending}>
          {auditMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Run Technical Audit
        </Button>
        <Button variant="outline" onClick={() => digestMutation.mutate()} disabled={digestMutation.isPending}>
          {digestMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Generate Digest
        </Button>
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
              <Sparkles className="h-4 w-4 text-brand-500" />
              Latest Digest
            </h2>
            {latestDigest && (
              <div className="flex items-center gap-2">
                <span className="text-theme-xs text-gray-400">{latestDigest.run_date}</span>
                <Badge variant={latestDigest.slack_delivered ? "success" : "outline"}>
                  {latestDigest.slack_delivered ? "Sent to Slack" : "Not sent to Slack"}
                </Badge>
              </div>
            )}
          </div>
          {digestsQuery.isLoading ? (
            <div className="flex h-20 items-center justify-center text-gray-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : latestDigest ? (
            <p className="whitespace-pre-line text-theme-sm text-gray-700 dark:text-gray-300">
              {latestDigest.narrative}
            </p>
          ) : (
            <p className="text-theme-sm text-gray-400">
              No digest generated yet. Click "Generate Digest" to create today's.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SearchConsolePanel siteId={siteId} />
        <AnalyticsPanel siteId={siteId} />
      </div>

      <JobHistoryPanel jobs={jobs} loading={jobsQuery.isLoading} />

      <Card>
        <CardContent className="p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
              <AlertTriangle className="h-4 w-4 text-brand-500" />
              Technical Issues
            </h2>
            <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-white/5">
              {(["pending", "approved", "rejected", "all"] as IssueFilter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setIssueFilter(f)}
                  className={`rounded-md px-3 py-1 text-theme-xs font-medium capitalize transition-colors ${
                    issueFilter === f
                      ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white"
                      : "text-gray-500"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {issuesQuery.isLoading ? (
            <div className="flex h-32 items-center justify-center text-gray-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : issues.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-center">
              <CheckCircle2 className="h-8 w-8 text-success-400" />
              <p className="text-theme-sm text-gray-400">
                No {issueFilter !== "all" ? issueFilter : ""} issues. Run a technical audit to check for some.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {issues.map((issue) => (
                <div
                  key={issue.id}
                  className="rounded-lg border border-gray-100 p-4 transition-colors hover:border-gray-200 dark:border-gray-800 dark:hover:border-gray-700"
                >
                  <div className="mb-1.5 flex flex-wrap items-center gap-2">
                    <Badge variant={severityVariant[issue.severity]}>{issue.severity}</Badge>
                    <Badge variant="outline">{issue.rule.replace(/_/g, " ")}</Badge>
                    <Badge variant={issueStatusVariant[issue.status]}>{issue.status}</Badge>
                  </div>
                  <p className="break-all text-theme-xs text-gray-400">{issue.url}</p>
                  <p className="mt-1 text-theme-sm text-gray-700 dark:text-gray-300">{issue.message}</p>
                  <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">
                    Suggested fix: {issue.suggested_fix}
                  </p>

                  {REMEDIABLE_RULES.includes(issue.rule) ? (
                    <div className="mt-3 rounded-md bg-gray-50 p-3 dark:bg-white/5">
                      {issue.fix_value ? (
                        <>
                          <p className="text-theme-xs font-medium text-gray-500 dark:text-gray-400">
                            {issue.fix_applied ? "Applied to the live site:" : "Ready to apply:"}
                          </p>
                          <p className="mt-1 break-all text-theme-sm text-gray-800 dark:text-gray-200">
                            {issue.fix_value}
                          </p>
                          {issue.fix_applied && (
                            <Badge variant="success" className="mt-2">
                              <CheckCircle2 className="h-3 w-3" />
                              Live
                            </Badge>
                          )}
                          {issue.fix_error && !issue.fix_applied && (
                            <p className="mt-2 text-theme-xs text-error-500">{issue.fix_error}</p>
                          )}
                        </>
                      ) : (
                        <p className="text-theme-xs text-gray-400">
                          A real, ready-to-use fix can be generated for this issue.
                        </p>
                      )}
                      {!issue.fix_applied && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => generateFixMutation.mutate(issue.id)}
                            disabled={generateFixMutation.isPending}
                          >
                            {generateFixMutation.isPending ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Sparkles className="h-3.5 w-3.5" />
                            )}
                            {issue.fix_value ? "Regenerate fix" : "Generate fix"}
                          </Button>
                          {issue.fix_value && issue.status === "approved" && (
                            <Button size="sm" onClick={() => applyFixMutation.mutate(issue.id)} disabled={applyFixMutation.isPending}>
                              {applyFixMutation.isPending ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Send className="h-3.5 w-3.5" />
                              )}
                              Apply to website
                            </Button>
                          )}
                          {issue.fix_value && issue.status !== "approved" && (
                            <span className="self-center text-theme-xs text-gray-400">Approve this issue to apply the fix</span>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="mt-2 text-theme-xs text-gray-400">
                      Structural issue — needs a manual fix, can't be auto-applied.
                    </p>
                  )}

                  {issue.status === "pending" && (
                    <div className="mt-3 flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => approveMutation.mutate(issue.id)}>
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Approve
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => rejectMutation.mutate(issue.id)}>
                        <XCircle className="h-3.5 w-3.5" />
                        Reject
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <GoogleConfigCard site={site} />
      <CmsConfigCard site={site} />
      <ServerAccessConfigCard site={site} />
      <ServerFileBrowser site={site} />
    </>
  );
}

function JobHistoryPanel({ jobs, loading }: { jobs: SeoJobRun[]; loading: boolean }) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <History className="h-4 w-4 text-brand-500" />
          Automation Job History
        </h2>
        {loading ? (
          <div className="flex h-24 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : jobs.length === 0 ? (
          <p className="text-theme-sm text-gray-400">No automated runs yet — the daily cycle hasn't fired.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                  <th className="pb-2 pr-4 font-medium">Step</th>
                  <th className="pb-2 pr-4 font-medium">Date</th>
                  <th className="pb-2 pr-4 font-medium">Status</th>
                  <th className="pb-2 pr-4 font-medium">Finished</th>
                  <th className="pb-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => {
                  const isExpanded = expandedId === job.id;
                  return (
                    <Fragment key={job.id}>
                      <tr
                        className="cursor-pointer border-b border-gray-50 last:border-0 hover:bg-gray-50 dark:border-gray-800/50 dark:hover:bg-white/5"
                        onClick={() => setExpandedId(isExpanded ? null : job.id)}
                      >
                        <td className="py-2 pr-4 text-theme-sm text-gray-700 dark:text-gray-300">
                          {formatJobType(job.job_type)}
                        </td>
                        <td className="py-2 pr-4 text-theme-xs text-gray-400">{job.run_date}</td>
                        <td className="py-2 pr-4">
                          <Badge variant={jobStatusVariant[job.status]} className="capitalize">
                            {job.status === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
                            {job.status === "success" && <CheckCircle2 className="h-3 w-3" />}
                            {job.status === "failed" && <XCircle className="h-3 w-3" />}
                            {job.status}
                          </Badge>
                        </td>
                        <td className="py-2 pr-4 text-theme-xs text-gray-400">
                          {job.finished_at ? job.finished_at.replace("T", " ").slice(0, 19) : "—"}
                          {job.error && <span className="ml-1 text-error-500">(failed — click for details)</span>}
                        </td>
                        <td className="py-2 text-theme-xs text-brand-500">{isExpanded ? "Hide" : "Details"}</td>
                      </tr>
                      {isExpanded && (
                        <tr className="border-b border-gray-50 last:border-0 dark:border-gray-800/50">
                          <td colSpan={5} className="bg-gray-50 px-3 py-3 text-theme-xs dark:bg-white/5">
                            <div className="grid gap-1.5 sm:grid-cols-2">
                              <div>
                                <span className="text-gray-400">Job:</span>{" "}
                                <span className="text-gray-700 dark:text-gray-300">{formatJobType(job.job_type)}</span>
                              </div>
                              <div>
                                <span className="text-gray-400">Site:</span>{" "}
                                <span className="text-gray-700 dark:text-gray-300">{job.site_id}</span>
                              </div>
                              <div>
                                <span className="text-gray-400">Started:</span>{" "}
                                <span className="text-gray-700 dark:text-gray-300">{formatUtcTimestamp(job.started_at)}</span>
                              </div>
                              <div>
                                <span className="text-gray-400">Finished:</span>{" "}
                                <span className="text-gray-700 dark:text-gray-300">{formatUtcTimestamp(job.finished_at)}</span>
                              </div>
                            </div>
                            {job.error && (
                              <div className="mt-2">
                                <p className="mb-1 text-gray-400">Error:</p>
                                <pre className="whitespace-pre-wrap break-all rounded-md border border-gray-200 bg-white p-2 font-mono text-error-500 dark:border-gray-800 dark:bg-gray-900">
                                  {job.error}
                                </pre>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SearchConsolePanel({ siteId }: { siteId: number }) {
  const query = useQuery({ queryKey: ["seo", "gsc", siteId], queryFn: () => getGscQueries(siteId, 8) });
  const rows = query.data ?? [];

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Search className="h-4 w-4 text-brand-500" />
          Top Search Queries
        </h2>
        {query.isLoading ? (
          <div className="flex h-20 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : rows.length === 0 ? (
          <p className="text-theme-sm text-gray-400">
            No Search Console data yet — the daily pull hasn't found any queries for this property.
          </p>
        ) : (
          <div className="space-y-2">
            {rows.map((row: GscQueryRow) => (
              <div key={row.id} className="flex items-center justify-between gap-3 text-theme-sm">
                <span className="truncate text-gray-700 dark:text-gray-300">{row.query}</span>
                <span className="shrink-0 text-theme-xs text-gray-400">
                  {row.clicks} clicks · {row.impressions} impr.
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AnalyticsPanel({ siteId }: { siteId: number }) {
  const query = useQuery({ queryKey: ["seo", "ga4", siteId], queryFn: () => getGa4Pages(siteId, 8) });
  const rows = query.data ?? [];

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <BarChart3 className="h-4 w-4 text-brand-500" />
          Top Traffic Pages
        </h2>
        {query.isLoading ? (
          <div className="flex h-20 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : rows.length === 0 ? (
          <p className="text-theme-sm text-gray-400">
            No Analytics data yet — the daily pull hasn't found any sessions for this property.
          </p>
        ) : (
          <div className="space-y-2">
            {rows.map((row: Ga4PageRow) => (
              <div key={row.id} className="flex items-center justify-between gap-3 text-theme-sm">
                <span className="truncate text-gray-700 dark:text-gray-300">{row.page_path}</span>
                <span className="shrink-0 text-theme-xs text-gray-400">{row.sessions} sessions</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SocialTab({ siteId }: { siteId: number }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [pageTitle, setPageTitle] = useState("");
  const [contentExcerpt, setContentExcerpt] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<SocialPlatform[]>(["linkedin"]);

  const postsQuery = useQuery({ queryKey: ["seo", "social", siteId], queryFn: () => getSocialPosts(siteId) });
  const posts = postsQuery.data ?? [];

  const generateMutation = useMutation({
    mutationFn: () =>
      generateSocialPosts({
        site_id: siteId,
        page_title: pageTitle,
        content_excerpt: contentExcerpt,
        image_url: imageUrl.trim() || undefined,
        platforms: selectedPlatforms,
      }),
    onSuccess: (created) => {
      toast.success(`Generated ${created.length} of ${selectedPlatforms.length} requested post(s).`);
      queryClient.invalidateQueries({ queryKey: ["seo", "social", siteId] });
    },
    onError: () => toast.error("Social content generation failed — check that Ollama is running."),
  });

  const approveMutation = useMutation({
    mutationFn: (id: number) => approveSocialPost(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "social", siteId] }),
  });
  const rejectMutation = useMutation({
    mutationFn: (id: number) => rejectSocialPost(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "social", siteId] }),
  });
  const publishMutation = useMutation({
    mutationFn: (id: number) => publishSocialPost(id),
    onSuccess: (result) => {
      if (result.status === "posted") {
        toast.success(`Posted to ${result.platform}.`);
      } else {
        toast.info(result.error || "No automated posting exists for this platform — post it manually.");
      }
      queryClient.invalidateQueries({ queryKey: ["seo", "social", siteId] });
    },
  });

  const togglePlatform = (p: SocialPlatform) => {
    setSelectedPlatforms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));
  };

  return (
    <>
      <Card>
        <CardContent className="p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <Sparkles className="h-4 w-4 text-brand-500" />
            Generate social content
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="social-title">Page title</Label>
              <Input id="social-title" value={pageTitle} onChange={(e) => setPageTitle(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="social-excerpt">Content excerpt</Label>
              <Input id="social-excerpt" value={contentExcerpt} onChange={(e) => setContentExcerpt(e.target.value)} />
            </div>
            <div className="sm:col-span-2">
              <Label htmlFor="social-image-url">
                Image URL{selectedPlatforms.includes("instagram") ? " (required for Instagram)" : " (optional)"}
              </Label>
              <Input
                id="social-image-url"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                placeholder="https://example.com/page-image.jpg"
              />
              {selectedPlatforms.includes("instagram") && !imageUrl.trim() && (
                <p className="mt-1 text-theme-xs text-warning-500">
                  Instagram has no text-only post type — this post won't be publishable there without an image URL.
                </p>
              )}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {ALL_PLATFORMS.map((p) => {
              const PlatformIcon = PLATFORM_ICONS[p];
              return (
                <button
                  key={p}
                  onClick={() => togglePlatform(p)}
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-theme-xs font-medium capitalize transition-colors ${
                    selectedPlatforms.includes(p)
                      ? "border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300"
                      : "border-gray-300 text-gray-600 dark:border-gray-700 dark:text-gray-300"
                  }`}
                >
                  <PlatformIcon className="h-3.5 w-3.5" />
                  {p}
                </button>
              );
            })}
          </div>
          <Button
            className="mt-4"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending || !pageTitle.trim() || !contentExcerpt.trim() || selectedPlatforms.length === 0}
          >
            {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Generate
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <Share2 className="h-4 w-4 text-brand-500" />
            Posts
          </h2>
          {postsQuery.isLoading ? (
            <div className="flex h-24 items-center justify-center text-gray-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : posts.length === 0 ? (
            <p className="text-theme-sm text-gray-400">No social posts yet — generate some above.</p>
          ) : (
            <div className="space-y-3">
              {posts.map((post) => (
                <div key={post.id} className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                  <div className="mb-1.5 flex items-center gap-2">
                    <Badge variant="outline" className="capitalize">
                      {(() => {
                        const PlatformIcon = PLATFORM_ICONS[post.platform];
                        return <PlatformIcon className="h-3 w-3" />;
                      })()}
                      {post.platform}
                    </Badge>
                    <Badge variant={socialStatusVariant[post.status]}>{post.status}</Badge>
                  </div>
                  {post.image_url && (
                    <img
                      src={post.image_url}
                      alt=""
                      className="mb-2 h-32 w-32 rounded-md object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  )}
                  <p className="whitespace-pre-line text-theme-sm text-gray-700 dark:text-gray-300">{post.content}</p>
                  {post.platform === "instagram" && !post.image_url && (
                    <p className="mt-1 text-theme-xs text-warning-500">
                      No image URL — this post can't be published to Instagram until one is added.
                    </p>
                  )}
                  {post.error && <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">{post.error}</p>}
                  {post.status === "draft" && (
                    <div className="mt-3 flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => approveMutation.mutate(post.id)}>
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Approve
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => rejectMutation.mutate(post.id)}>
                        <XCircle className="h-3.5 w-3.5" />
                        Reject
                      </Button>
                    </div>
                  )}
                  {(post.status === "approved" || post.status === "failed") && (
                    <Button
                      size="sm"
                      className="mt-3"
                      onClick={() => publishMutation.mutate(post.id)}
                      disabled={publishMutation.isPending}
                    >
                      {publishMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                      {post.status === "failed" ? "Retry publish" : "Publish"}
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

function BlogTab({ siteId }: { siteId: number }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [topic, setTopic] = useState("");
  const [primaryKeyword, setPrimaryKeyword] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editExcerpt, setEditExcerpt] = useState("");
  const [editContent, setEditContent] = useState("");

  const postsQuery = useQuery({ queryKey: ["seo", "blog", siteId], queryFn: () => getBlogPosts(siteId) });
  const posts = postsQuery.data ?? [];

  const startEditing = (post: BlogPost) => {
    setEditingId(post.id);
    setEditTitle(post.title);
    setEditExcerpt(post.excerpt ?? "");
    setEditContent(post.content);
    setExpandedId(post.id);
  };

  const updateMutation = useMutation({
    mutationFn: (postId: number) => updateBlogPost(postId, { title: editTitle, excerpt: editExcerpt, content: editContent }),
    onSuccess: () => {
      toast.success("Draft updated.");
      setEditingId(null);
      queryClient.invalidateQueries({ queryKey: ["seo", "blog", siteId] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Could not save these changes.")),
  });

  const generateMutation = useMutation({
    mutationFn: () => generateBlogPost({ site_id: siteId, topic, primary_keyword: primaryKeyword.trim() || undefined }),
    onSuccess: () => {
      toast.success("Blog post drafted.");
      queryClient.invalidateQueries({ queryKey: ["seo", "blog", siteId] });
    },
    onError: () => toast.error("Blog post generation failed — check that Ollama is running."),
  });

  const approveMutation = useMutation({
    mutationFn: (id: number) => approveBlogPost(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "blog", siteId] }),
  });
  const rejectMutation = useMutation({
    mutationFn: (id: number) => rejectBlogPost(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "blog", siteId] }),
  });
  const publishMutation = useMutation({
    mutationFn: (id: number) => publishBlogPost(id),
    onSuccess: (result) => {
      if (result.status === "published") {
        toast.success("Created as a draft in your CMS — open it there to review and publish for real.");
      } else {
        toast.error(result.error || "Publishing to the CMS failed.");
      }
      queryClient.invalidateQueries({ queryKey: ["seo", "blog", siteId] });
    },
  });

  return (
    <>
      <Card>
        <CardContent className="p-6">
          <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <FileText className="h-4 w-4 text-brand-500" />
            Generate a blog post
          </h2>
          <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
            AI drafts a full post here for review. Once approved, "Publish" creates it as a real draft in your
            CMS (WordPress/Webflow) — never live — so you still do the final review and hit Publish yourself there.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="blog-topic">Topic</Label>
              <Input
                id="blog-topic"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. Why remote teams need activity tracking software"
              />
            </div>
            <div>
              <Label htmlFor="blog-keyword">Primary keyword (optional)</Label>
              <Input id="blog-keyword" value={primaryKeyword} onChange={(e) => setPrimaryKeyword(e.target.value)} />
            </div>
          </div>
          <Button
            className="mt-4"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending || !topic.trim()}
          >
            {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
            Generate
          </Button>
          {generateMutation.isPending && (
            <p className="mt-2 text-theme-xs text-gray-400">
              A full post takes a minute or two — this uses the slower, higher-quality model on purpose.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <FileText className="h-4 w-4 text-brand-500" />
            Drafts
          </h2>
          {postsQuery.isLoading ? (
            <div className="flex h-24 items-center justify-center text-gray-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : posts.length === 0 ? (
            <p className="text-theme-sm text-gray-400">No blog posts yet — generate one above.</p>
          ) : (
            <div className="space-y-3">
              {posts.map((post) => {
                const issues: StructureIssue[] = post.structure_issues_json ? JSON.parse(post.structure_issues_json) : [];
                return (
                  <div key={post.id} className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                    <div className="mb-1.5 flex flex-wrap items-center gap-2">
                      <Badge variant={blogStatusVariant[post.status]}>{post.status}</Badge>
                      {post.structure_passed !== null && (
                        <Badge variant={post.structure_passed ? "success" : "warning"}>
                          {post.structure_passed ? "structure OK" : `${issues.length} structure issue(s)`}
                        </Badge>
                      )}
                      {post.cms_post_link && (
                        <a
                          href={post.cms_post_link}
                          target="_blank"
                          rel="noreferrer"
                          className="text-theme-xs text-brand-600 underline dark:text-brand-400"
                        >
                          View draft in CMS
                        </a>
                      )}
                    </div>
                    <p className="font-medium text-gray-900 dark:text-white">{post.title}</p>
                    <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">{post.excerpt}</p>
                    {issues.length > 0 && (
                      <ul className="mt-2 space-y-0.5">
                        {issues.map((issue, idx) => (
                          <li key={idx} className="text-theme-xs text-gray-400">
                            <Badge variant={issue.severity === "error" ? "destructive" : "warning"} className="mr-1.5">
                              {issue.severity}
                            </Badge>
                            {issue.message}
                          </li>
                        ))}
                      </ul>
                    )}
                    {post.error && <p className="mt-1 text-theme-xs text-red-500">{post.error}</p>}
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <Button size="sm" variant="outline" onClick={() => setExpandedId(expandedId === post.id ? null : post.id)}>
                        {expandedId === post.id ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        {expandedId === post.id ? "Hide content" : "View content"}
                      </Button>
                      {post.status === "draft" && (
                        <>
                          <Button size="sm" variant="outline" onClick={() => startEditing(post)}>
                            <Pencil className="h-3.5 w-3.5" />
                            Edit
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => approveMutation.mutate(post.id)}>
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Approve
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => rejectMutation.mutate(post.id)}>
                            <XCircle className="h-3.5 w-3.5" />
                            Reject
                          </Button>
                        </>
                      )}
                      {(post.status === "approved" || post.status === "failed") && (
                        <Button size="sm" onClick={() => publishMutation.mutate(post.id)} disabled={publishMutation.isPending}>
                          <Send className="h-3.5 w-3.5" />
                          {post.status === "failed" ? "Retry publish" : "Publish"}
                        </Button>
                      )}
                    </div>
                    {expandedId === post.id && editingId === post.id ? (
                      <div className="mt-3 space-y-3 rounded-md bg-gray-50 p-4 dark:bg-white/5">
                        <div>
                          <Label htmlFor={`blog-edit-title-${post.id}`}>Title</Label>
                          <Input id={`blog-edit-title-${post.id}`} value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                        </div>
                        <div>
                          <Label htmlFor={`blog-edit-excerpt-${post.id}`}>Excerpt</Label>
                          <Input
                            id={`blog-edit-excerpt-${post.id}`}
                            value={editExcerpt}
                            onChange={(e) => setEditExcerpt(e.target.value)}
                          />
                        </div>
                        <div>
                          <Label htmlFor={`blog-edit-content-${post.id}`}>Content</Label>
                          <RichTextEditor value={editContent} onChange={setEditContent} headings placeholder="Post body…" />
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => updateMutation.mutate(post.id)}
                            disabled={updateMutation.isPending || !editTitle.trim() || !editContent.trim()}
                          >
                            {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                            Save
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => setEditingId(null)}>
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      expandedId === post.id && (
                        <div
                          className="prose prose-sm mt-3 max-w-none rounded-md bg-gray-50 p-4 dark:bg-white/5 dark:prose-invert"
                          dangerouslySetInnerHTML={{ __html: sanitizeBlogHtml(post.content) }}
                        />
                      )
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

// A score-against-a-limit is a meter, not a badge: the fill carries
// severity, the track is a lighter step of the same ramp so state reads
// across the whole bar even before the number registers.
function ScoreMeter({ score }: { score: number | null }) {
  if (score === null) {
    return <span className="text-theme-sm text-gray-400">No score yet</span>;
  }
  const pct = Math.max(0, Math.min(100, score));
  const tone = pct >= 90 ? "success" : pct >= 50 ? "warning" : "error";
  const trackClass = {
    success: "bg-success-50 dark:bg-success-500/10",
    warning: "bg-warning-50 dark:bg-warning-500/10",
    error: "bg-error-50 dark:bg-error-500/10",
  }[tone];
  const fillClass = { success: "bg-success-500", warning: "bg-warning-500", error: "bg-error-500" }[tone];
  const textClass = {
    success: "text-success-700 dark:text-success-400",
    warning: "text-warning-700 dark:text-warning-400",
    error: "text-error-700 dark:text-error-400",
  }[tone];
  return (
    <div className="flex items-center gap-2.5">
      <div className={`h-2 w-28 overflow-hidden rounded-full ${trackClass}`}>
        <div className={`h-full rounded-full ${fillClass} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-theme-sm font-semibold ${textClass}`}>{Math.round(pct)}</span>
    </div>
  );
}

function formatKb(kb: number | null) {
  if (kb === null) return "—";
  return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.round(kb)} KB`;
}

function formatMs(ms: number | null) {
  if (ms === null) return "—";
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
}

function OpportunitiesPanel({ resultId }: { resultId: number }) {
  const oppQuery = useQuery({
    queryKey: ["seo", "pagespeed-opportunities", resultId],
    queryFn: () => getPageSpeedOpportunities(resultId),
  });

  if (oppQuery.isLoading) {
    return (
      <div className="flex h-16 items-center justify-center text-gray-400">
        <Loader2 className="h-4 w-4 animate-spin" />
      </div>
    );
  }
  if (oppQuery.isError) {
    return <p className="text-theme-xs text-gray-400">Could not load the resource audit for this result.</p>;
  }
  const report = oppQuery.data;
  if (!report) return null;

  return (
    <div className="mt-3 space-y-3 border-t border-gray-100 pt-3 dark:border-gray-800">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <div>
          <p className="text-theme-xs text-gray-400">Requests</p>
          <p className="text-theme-sm font-medium text-gray-900 dark:text-white">{report.total_requests ?? "—"}</p>
        </div>
        <div>
          <p className="text-theme-xs text-gray-400">Page weight</p>
          <p className="text-theme-sm font-medium text-gray-900 dark:text-white">{formatKb(report.total_byte_weight_kb)}</p>
        </div>
        <div>
          <p className="text-theme-xs text-gray-400">Unused CSS</p>
          <p className="text-theme-sm font-medium text-gray-900 dark:text-white">{formatKb(report.unused_css_kb)}</p>
        </div>
        <div>
          <p className="text-theme-xs text-gray-400">Unused JS</p>
          <p className="text-theme-sm font-medium text-gray-900 dark:text-white">{formatKb(report.unused_js_kb)}</p>
        </div>
        <div>
          <p className="text-theme-xs text-gray-400">Render-blocking</p>
          <p className="text-theme-sm font-medium text-gray-900 dark:text-white">{report.render_blocking_requests ?? 0}</p>
        </div>
      </div>

      {report.opportunities.length === 0 ? (
        <p className="text-theme-xs text-gray-400">No specific fix-list opportunities found — this page is already well optimized.</p>
      ) : (
        <div className="space-y-2">
          <p className="text-theme-xs font-medium text-gray-500 dark:text-gray-400">Prioritized fix list</p>
          {report.opportunities.map((o) => (
            <div key={o.audit_id} className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-theme-sm font-medium text-gray-900 dark:text-white">{o.title}</p>
                <span className="text-theme-xs text-gray-400">
                  {o.savings_ms ? `~${formatMs(o.savings_ms)} saved` : o.savings_bytes ? `~${formatKb(o.savings_bytes / 1024)} saved` : ""}
                </span>
              </div>
              {o.description && (
                <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">{o.description.replace(/\[.*?\]\(.*?\)/g, "").trim()}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PerformanceTab({ siteId, siteUrl }: { siteId: number; siteUrl: string }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [checkUrl, setCheckUrl] = useState(siteUrl);
  const [strategy, setStrategy] = useState<PageSpeedStrategy>("mobile");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const resultsQuery = useQuery({ queryKey: ["seo", "pagespeed", siteId], queryFn: () => getPageSpeedResults(siteId) });
  const results = resultsQuery.data ?? [];

  const checkMutation = useMutation({
    mutationFn: () => checkPageSpeed(siteId, checkUrl.trim(), strategy),
    onSuccess: (result: PageSpeedResult) => {
      toast.success(`PageSpeed check complete: score ${Math.round(result.performance_score ?? 0)}.`);
      queryClient.invalidateQueries({ queryKey: ["seo", "pagespeed", siteId] });
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "PageSpeed check failed — Google's free anonymous quota may be exhausted; try again shortly, or set PAGESPEED_API_KEY.");
    },
  });

  return (
    <>
      <Card>
        <CardContent className="p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <Gauge className="h-4 w-4 text-brand-500" />
            Page Speed check
          </h2>
          <div className="grid gap-4 sm:grid-cols-[1fr_auto]">
            <div>
              <Label htmlFor="ps-url">URL</Label>
              <Input id="ps-url" value={checkUrl} onChange={(e) => setCheckUrl(e.target.value)} placeholder={siteUrl} />
            </div>
            <div>
              <Label htmlFor="ps-strategy">Strategy</Label>
              <select
                id="ps-strategy"
                value={strategy}
                onChange={(e) => setStrategy(e.target.value as PageSpeedStrategy)}
                className="h-11 rounded-lg border border-gray-300 bg-transparent px-4 text-sm text-gray-800 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
              >
                <option value="mobile">Mobile</option>
                <option value="desktop">Desktop</option>
              </select>
            </div>
          </div>
          <Button
            className="mt-4"
            onClick={() => checkMutation.mutate()}
            disabled={checkMutation.isPending || !checkUrl.trim()}
          >
            {checkMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Gauge className="h-4 w-4" />}
            Run Page Speed Check
          </Button>
          {checkMutation.isPending && (
            <p className="mt-2 text-theme-xs text-gray-400">
              Lighthouse runs server-side on Google's end — this genuinely takes 20-40 seconds for a real page, longer for a slow or heavy one.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <BarChart3 className="h-4 w-4 text-brand-500" />
            Results
          </h2>
          {resultsQuery.isLoading ? (
            <div className="flex h-24 items-center justify-center text-gray-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : results.length === 0 ? (
            <p className="text-theme-sm text-gray-400">No checks yet — run one above.</p>
          ) : (
            <div className="space-y-3">
              {results.map((r) => (
                <div key={r.id} className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <ScoreMeter score={r.performance_score} />
                      <Badge variant="outline" className="capitalize">{r.strategy}</Badge>
                      <span className="text-theme-xs text-gray-400">{r.run_date}</span>
                    </div>
                    <Button size="sm" variant="outline" onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}>
                      {expandedId === r.id ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      {expandedId === r.id ? "Hide fix list" : "View fix list"}
                    </Button>
                  </div>
                  <p className="mt-1 break-all text-theme-xs text-gray-400">{r.url}</p>
                  <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-5">
                    <div>
                      <p className="text-theme-xs text-gray-400">LCP</p>
                      <p className="text-theme-sm text-gray-700 dark:text-gray-300">{formatMs(r.lcp_ms)}</p>
                    </div>
                    <div>
                      <p className="text-theme-xs text-gray-400">CLS</p>
                      <p className="text-theme-sm text-gray-700 dark:text-gray-300">{r.cls?.toFixed(3) ?? "—"}</p>
                    </div>
                    <div>
                      <p className="text-theme-xs text-gray-400">INP</p>
                      <p className="text-theme-sm text-gray-700 dark:text-gray-300">{formatMs(r.inp_ms)}</p>
                    </div>
                    <div>
                      <p className="text-theme-xs text-gray-400">TTFB</p>
                      <p className="text-theme-sm text-gray-700 dark:text-gray-300">{formatMs(r.ttfb_ms)}</p>
                    </div>
                    <div>
                      <p className="text-theme-xs text-gray-400">FCP</p>
                      <p className="text-theme-sm text-gray-700 dark:text-gray-300">{formatMs(r.fcp_ms)}</p>
                    </div>
                  </div>
                  {expandedId === r.id && <OpportunitiesPanel resultId={r.id} />}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

function IndexingTab({ siteId, siteUrl }: { siteId: number; siteUrl: string }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [inspectUrlInput, setInspectUrlInput] = useState(siteUrl);
  const [submitUrlInput, setSubmitUrlInput] = useState(siteUrl);
  const [notificationType, setNotificationType] = useState<IndexingNotificationType>("URL_UPDATED");

  const statusQuery = useQuery({ queryKey: ["seo", "index-status", siteId], queryFn: () => getIndexStatusList(siteId) });
  const statuses = statusQuery.data ?? [];

  const submissionsQuery = useQuery({
    queryKey: ["seo", "indexing-submissions", siteId],
    queryFn: () => getIndexingSubmissions(siteId),
  });
  const submissions = submissionsQuery.data ?? [];

  const inspectMutation = useMutation({
    mutationFn: () => inspectUrl(siteId, inspectUrlInput.trim()),
    onSuccess: (result) => {
      toast.success(`Inspected: ${result.coverage_state ?? "no coverage state returned"}.`);
      queryClient.invalidateQueries({ queryKey: ["seo", "index-status", siteId] });
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "URL Inspection failed — see server logs.");
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => submitForIndexing(siteId, submitUrlInput.trim(), notificationType),
    onSuccess: (result) => {
      if (result.success) {
        toast.success("Submitted to Google's Indexing API.");
      } else {
        toast.info(result.error || "Submission failed — see the log below.");
      }
      queryClient.invalidateQueries({ queryKey: ["seo", "indexing-submissions", siteId] });
    },
  });

  return (
    <>
      <Card>
        <CardContent className="p-6">
          <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <Search className="h-4 w-4 text-brand-500" />
            Index coverage
          </h2>
          <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
            Real-time index status from Google Search Console's URL Inspection API.
          </p>
          <div className="flex flex-wrap gap-3">
            <div className="min-w-64 flex-1">
              <Label htmlFor="inspect-url">URL</Label>
              <Input id="inspect-url" value={inspectUrlInput} onChange={(e) => setInspectUrlInput(e.target.value)} placeholder={siteUrl} />
            </div>
            <div className="flex items-end">
              <Button onClick={() => inspectMutation.mutate()} disabled={inspectMutation.isPending || !inspectUrlInput.trim()}>
                {inspectMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                Inspect
              </Button>
            </div>
          </div>

          {statusQuery.isLoading ? (
            <div className="mt-4 flex h-16 items-center justify-center text-gray-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : statuses.length === 0 ? (
            <p className="mt-4 text-theme-sm text-gray-400">No URLs inspected yet.</p>
          ) : (
            <div className="mt-4 space-y-3">
              {statuses.map((s) => (
                <div key={s.id} className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                  <p className="break-all text-theme-sm font-medium text-gray-900 dark:text-white">{s.url}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge variant={s.coverage_state?.toLowerCase().includes("indexed") && !s.coverage_state?.toLowerCase().includes("not") ? "success" : "outline"}>
                      {s.coverage_state ?? "unknown"}
                    </Badge>
                    {s.indexing_state && <Badge variant="outline">{s.indexing_state}</Badge>}
                    {s.robots_txt_state && <Badge variant="outline">robots.txt: {s.robots_txt_state}</Badge>}
                    {s.page_fetch_state && <Badge variant="outline">fetch: {s.page_fetch_state}</Badge>}
                  </div>
                  <p className="mt-2 text-theme-xs text-gray-400">
                    {s.last_crawl_time ? `Last crawled ${s.last_crawl_time}` : "Never crawled by Google"} · checked {s.checked_at}
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <RefreshCw className="h-4 w-4 text-brand-500" />
            Request re-crawl
          </h2>
          <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
            Asks Google's Indexing API to recrawl a URL sooner. Google documents this API as intended for
            JobPosting/BroadcastEvent pages — for other content it may not be prioritized, and the underlying
            Google Cloud project needs the Indexing API explicitly enabled.
          </p>
          <div className="flex flex-wrap gap-3">
            <div className="min-w-64 flex-1">
              <Label htmlFor="submit-url">URL</Label>
              <Input id="submit-url" value={submitUrlInput} onChange={(e) => setSubmitUrlInput(e.target.value)} placeholder={siteUrl} />
            </div>
            <div>
              <Label htmlFor="notif-type">Type</Label>
              <select
                id="notif-type"
                value={notificationType}
                onChange={(e) => setNotificationType(e.target.value as IndexingNotificationType)}
                className="h-11 rounded-lg border border-gray-300 bg-transparent px-4 text-sm text-gray-800 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
              >
                <option value="URL_UPDATED">URL updated</option>
                <option value="URL_DELETED">URL deleted</option>
              </select>
            </div>
            <div className="flex items-end">
              <Button onClick={() => submitMutation.mutate()} disabled={submitMutation.isPending || !submitUrlInput.trim()}>
                {submitMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Submit
              </Button>
            </div>
          </div>

          {submissionsQuery.isLoading ? (
            <div className="mt-4 flex h-16 items-center justify-center text-gray-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : submissions.length === 0 ? (
            <p className="mt-4 text-theme-sm text-gray-400">No submissions yet.</p>
          ) : (
            <div className="mt-4 space-y-2">
              {submissions.map((s) => (
                <div key={s.id} className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={s.success ? "success" : "destructive"}>{s.success ? "submitted" : "failed"}</Badge>
                    <Badge variant="outline">{s.notification_type}</Badge>
                    <span className="text-theme-xs text-gray-400">{s.submitted_at}</span>
                  </div>
                  <p className="mt-1 break-all text-theme-xs text-gray-400">{s.url}</p>
                  {s.error && <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">{s.error}</p>}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

function numOrDash(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : value.toLocaleString();
}

function SemrushDomainOverview({ siteId }: { siteId: number }) {
  const queryClient = useQueryClient();
  const toast = useToast();

  const metricsQuery = useQuery({
    queryKey: ["seo", "semrush", siteId],
    queryFn: () => getSemrushMetrics(siteId, 1),
  });
  const latest = metricsQuery.data?.[0] ?? null;

  const checkMutation = useMutation({
    mutationFn: () => checkSemrushMetrics(siteId),
    onSuccess: () => {
      toast.success("Semrush domain metrics refreshed.");
      queryClient.invalidateQueries({ queryKey: ["seo", "semrush", siteId] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Semrush fetch failed — check SEMRUSH_API_KEY and API unit balance.")),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-1 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <Award className="h-4 w-4 text-brand-500" />
            Domain Overview (Semrush)
          </h2>
          <Button size="sm" variant="outline" onClick={() => checkMutation.mutate()} disabled={checkMutation.isPending}>
            {checkMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Refresh
          </Button>
        </div>
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          Authority Score, organic/paid keyword counts, organic traffic, referring domains and total backlinks — pulled
          from Semrush's Domain Overview and Backlinks Overview reports. This spends real Semrush API units on every
          refresh; Semrush's API is unit-based under a paid plan, not a standing free tier — set SEMRUSH_API_KEY in
          .env to enable it.
          {latest && <span className="ml-1">Last checked {latest.run_date}.</span>}
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          <StatCard label="Authority Score" value={numOrDash(latest?.authority_score ?? null)} icon={Award} loading={metricsQuery.isLoading} />
          <StatCard label="Semrush Rank" value={numOrDash(latest?.semrush_rank ?? null)} icon={Hash} loading={metricsQuery.isLoading} />
          <StatCard label="Organic Traffic" value={numOrDash(latest?.organic_traffic ?? null)} icon={TrendingUp} loading={metricsQuery.isLoading} />
          <StatCard label="Organic Keywords" value={numOrDash(latest?.organic_keywords ?? null)} icon={Search} loading={metricsQuery.isLoading} />
          <StatCard label="Paid Keywords" value={numOrDash(latest?.paid_keywords ?? null)} icon={BarChart3} loading={metricsQuery.isLoading} />
          <StatCard label="Ref. Domains" value={numOrDash(latest?.referring_domains ?? null)} icon={Globe} loading={metricsQuery.isLoading} />
          <StatCard label="Backlinks" value={numOrDash(latest?.backlinks_total ?? null)} icon={Link2} loading={metricsQuery.isLoading} />
        </div>
        {!latest && !metricsQuery.isLoading && (
          <p className="mt-4 text-theme-sm text-gray-400">No Semrush data yet — click Refresh to run the first check.</p>
        )}
      </CardContent>
    </Card>
  );
}

function SemrushLinkExplorer({ siteId }: { siteId: number }) {
  const [view, setView] = useState<"backlinks" | "referring-domains">("backlinks");

  const backlinksQuery = useQuery({
    queryKey: ["seo", "semrush-backlinks", siteId],
    queryFn: () => getSemrushBacklinks(siteId, 50),
    enabled: view === "backlinks",
  });
  const domainsQuery = useQuery({
    queryKey: ["seo", "semrush-referring-domains", siteId],
    queryFn: () => getSemrushReferringDomains(siteId, 50),
    enabled: view === "referring-domains",
  });

  const activeQuery = view === "backlinks" ? backlinksQuery : domainsQuery;

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <Link2 className="h-4 w-4 text-brand-500" />
            Backlinks & Referring Domains (Semrush)
          </h2>
          <div className="flex gap-2">
            <Button size="sm" variant={view === "backlinks" ? "default" : "outline"} onClick={() => setView("backlinks")}>
              Backlinks
            </Button>
            <Button
              size="sm"
              variant={view === "referring-domains" ? "default" : "outline"}
              onClick={() => setView("referring-domains")}
            >
              Referring Domains
            </Button>
          </div>
        </div>

        {activeQuery.isError ? (
          <p className="text-theme-sm text-error-500">{serverErrorDetail(activeQuery.error, "Semrush fetch failed.")}</p>
        ) : activeQuery.isLoading ? (
          <div className="flex h-24 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : view === "backlinks" ? (
          (backlinksQuery.data ?? []).length === 0 ? (
            <p className="text-theme-sm text-gray-400">No backlink rows — check SEMRUSH_API_KEY, or this domain has none on record.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-theme-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                    <th className="py-2 pr-3 font-medium">Source</th>
                    <th className="py-2 pr-3 font-medium">Anchor</th>
                    <th className="py-2 pr-3 font-medium">Follow</th>
                    <th className="py-2 pr-3 font-medium">Page AS</th>
                    <th className="py-2 font-medium">First seen</th>
                  </tr>
                </thead>
                <tbody>
                  {(backlinksQuery.data ?? []).map((row: SemrushBacklinkRow, i: number) => (
                    <tr key={i} className="border-b border-gray-50 last:border-b-0 dark:border-gray-800/50">
                      <td className="max-w-xs truncate py-2 pr-3">
                        <a href={row.source_url} target="_blank" rel="noreferrer" className="text-brand-500 hover:underline">
                          {row.source_url}
                        </a>
                      </td>
                      <td className="max-w-[10rem] truncate py-2 pr-3 text-gray-500 dark:text-gray-400">{row.anchor || "—"}</td>
                      <td className="py-2 pr-3">
                        <Badge variant={row.nofollow ? "outline" : "success"}>{row.nofollow ? "nofollow" : "follow"}</Badge>
                      </td>
                      <td className="py-2 pr-3">{numOrDash(row.page_authority_score)}</td>
                      <td className="py-2 text-gray-400">{row.first_seen || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (domainsQuery.data ?? []).length === 0 ? (
          <p className="text-theme-sm text-gray-400">No referring domains — check SEMRUSH_API_KEY, or this domain has none on record.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-theme-sm">
              <thead>
                <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                  <th className="py-2 pr-3 font-medium">Domain</th>
                  <th className="py-2 pr-3 font-medium">Authority Score</th>
                  <th className="py-2 pr-3 font-medium">Backlinks</th>
                  <th className="py-2 font-medium">Country</th>
                </tr>
              </thead>
              <tbody>
                {(domainsQuery.data ?? []).map((row: SemrushReferringDomainRow, i: number) => (
                  <tr key={i} className="border-b border-gray-50 last:border-b-0 dark:border-gray-800/50">
                    <td className="py-2 pr-3">{row.domain}</td>
                    <td className="py-2 pr-3">{numOrDash(row.authority_score)}</td>
                    <td className="py-2 pr-3">{numOrDash(row.backlinks_num)}</td>
                    <td className="py-2 text-gray-400">{row.country || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SemrushBacklinkGapCard({ siteId }: { siteId: number }) {
  const toast = useToast();
  const [competitorInput, setCompetitorInput] = useState("");
  const [rows, setRows] = useState<SemrushGapRow[] | null>(null);

  const gapMutation = useMutation({
    mutationFn: (competitors: string[]) => getSemrushBacklinkGap(siteId, competitors),
    onSuccess: (data) => setRows(data),
    onError: (err) => toast.error(serverErrorDetail(err, "Backlink Gap check failed.")),
  });

  const handleCompare = () => {
    const competitors = competitorInput
      .split(",")
      .map((d) => d.trim())
      .filter(Boolean);
    if (competitors.length === 0) {
      toast.error("Enter at least one competitor domain.");
      return;
    }
    gapMutation.mutate(competitors);
  };

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <BarChart3 className="h-4 w-4 text-brand-500" />
          Backlink Gap (Semrush)
        </h2>
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          Compares this site's Authority Score/backlinks/referring domains against one or more competitor domains.
          Real Semrush comparison data (`backlinks_comparison`), aggregate stats only — not the same per-URL overlap
          detail as Semrush's own Backlink Gap tool.
        </p>
        <div className="flex gap-2">
          <Input
            value={competitorInput}
            onChange={(e) => setCompetitorInput(e.target.value)}
            placeholder="competitor1.com, competitor2.com"
            className="flex-1"
          />
          <Button size="sm" onClick={handleCompare} disabled={gapMutation.isPending}>
            {gapMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Compare
          </Button>
        </div>
        {rows && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-theme-sm">
              <thead>
                <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                  <th className="py-2 pr-3 font-medium">Domain</th>
                  <th className="py-2 pr-3 font-medium">Authority Score</th>
                  <th className="py-2 pr-3 font-medium">Backlinks</th>
                  <th className="py-2 font-medium">Ref. Domains</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i} className="border-b border-gray-50 last:border-b-0 dark:border-gray-800/50">
                    <td className="py-2 pr-3">{row.target}</td>
                    <td className="py-2 pr-3">{numOrDash(row.authority_score)}</td>
                    <td className="py-2 pr-3">{numOrDash(row.backlinks_num)}</td>
                    <td className="py-2">{numOrDash(row.referring_domains_num)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function BacklinksTab({ siteId, siteName, siteUrl }: { siteId: number; siteName: string; siteUrl: string }) {
  const queryClient = useQueryClient();
  const toast = useToast();

  const mentionsQuery = useQuery({ queryKey: ["seo", "backlinks", siteId], queryFn: () => getBacklinks(siteId) });
  const mentions = mentionsQuery.data ?? [];

  const pullMutation = useMutation({
    mutationFn: () => pullBacklinks(siteId),
    onSuccess: (found) => {
      toast.success(`Checked for mentions: ${found.length} on record.`);
      queryClient.invalidateQueries({ queryKey: ["seo", "backlinks", siteId] });
    },
    onError: () => toast.error("Mention check failed — is GOOGLE_ALERTS_RSS_URL configured?"),
  });

  const draftMutation = useMutation({
    mutationFn: (mentionId: number) => draftOutreachEmail(mentionId, siteName, siteUrl),
    onSuccess: () => {
      toast.success("Outreach email drafted.");
      queryClient.invalidateQueries({ queryKey: ["seo", "backlinks", siteId] });
    },
    onError: () => toast.error("Drafting failed — check that Ollama is running."),
  });

  return (
    <div className="space-y-6">
      <SemrushDomainOverview siteId={siteId} />
      <SemrushLinkExplorer siteId={siteId} />
      <SemrushBacklinkGapCard siteId={siteId} />
      <Card>
        <CardContent className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <Link2 className="h-4 w-4 text-brand-500" />
            Brand mentions
          </h2>
          <Button size="sm" onClick={() => pullMutation.mutate()} disabled={pullMutation.isPending}>
            {pullMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Check for mentions
          </Button>
        </div>
        {mentionsQuery.isLoading ? (
          <div className="flex h-24 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : mentions.length === 0 ? (
          <p className="text-theme-sm text-gray-400">
            No mentions on record. Free tier needs a Google Alerts RSS feed configured — see .env.example.
          </p>
        ) : (
          <div className="space-y-3">
            {mentions.map((m: BacklinkMention) => (
              <div key={m.id} className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                <p className="text-theme-sm font-medium text-gray-900 dark:text-white">{m.source_title || m.source_url}</p>
                <p className="break-all text-theme-xs text-gray-400">{m.source_url}</p>
                {m.outreach_subject ? (
                  <div className="mt-2 rounded-md bg-gray-50 p-3 dark:bg-white/5">
                    <p className="text-theme-xs font-medium text-gray-700 dark:text-gray-300">{m.outreach_subject}</p>
                    <p className="mt-1 whitespace-pre-line text-theme-xs text-gray-500 dark:text-gray-400">{m.outreach_body}</p>
                  </div>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-2"
                    onClick={() => draftMutation.mutate(m.id)}
                    disabled={draftMutation.isPending}
                  >
                    <Mail className="h-3.5 w-3.5" />
                    Draft outreach email
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
      </Card>
    </div>
  );
}

export default function SeoPage() {
  const [siteId, setSiteId] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [showAddSite, setShowAddSite] = useState(false);

  const sitesQuery = useQuery({ queryKey: ["seo", "sites"], queryFn: getSeoSites });
  const sites = sitesQuery.data ?? [];

  useEffect(() => {
    if (siteId === null && sites.length > 0) setSiteId(sites[0].id);
  }, [sites, siteId]);

  const selectedSite = sites.find((s) => s.id === siteId) ?? null;

  return (
    <>
      <PageMeta title="SEO | WorkPulse AI" description="Agentic SEO: audits, digests, social, and backlinks." />

      <div className="space-y-6">
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 via-brand-500 to-indigo-600 p-6 text-white shadow-lg shadow-brand-500/20 sm:p-8">
          <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
          <div className="relative flex flex-wrap items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-2.5">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/15">
                  <TrendingUp className="h-5 w-5" />
                </span>
                <h1 className="text-2xl font-bold sm:text-3xl">SEO</h1>
              </div>
              <p className="mt-2 max-w-xl text-sm text-white/80">
                Agentic SEO: technical audits, Search Console/Analytics, PageSpeed, digests, social and blog
                drafting, and backlink monitoring — the daily pipeline runs itself.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {sites.length > 0 && (
                <select
                  value={siteId ?? ""}
                  onChange={(e) => setSiteId(Number(e.target.value))}
                  className="h-11 rounded-lg border border-white/20 bg-white/10 px-4 text-sm font-medium text-white backdrop-blur-sm focus:outline-hidden focus:ring-2 focus:ring-white/40 [&>option]:text-gray-900"
                >
                  {sites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              )}
              {sites.length > 0 && !showAddSite && (
                <Button
                  variant="outline"
                  onClick={() => setShowAddSite(true)}
                  className="border-white/25 bg-white/10 text-white hover:bg-white/20"
                >
                  <Plus className="h-4 w-4" />
                  Add site
                </Button>
              )}
            </div>
          </div>
        </div>

        {sitesQuery.isLoading ? (
          <div className="flex h-40 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : sites.length === 0 || showAddSite ? (
          <NewSiteForm
            onCreated={(site) => {
              setSiteId(site.id);
              setShowAddSite(false);
            }}
            onCancel={sites.length > 0 ? () => setShowAddSite(false) : undefined}
          />
        ) : (
          selectedSite && (
            <>
              <div className="flex flex-wrap gap-1 rounded-lg bg-gray-100 p-1 dark:bg-white/5 w-fit">
                {TABS.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setTab(id)}
                    className={`flex items-center gap-1.5 rounded-md px-4 py-1.5 text-theme-sm font-medium transition-colors ${
                      tab === id
                        ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white"
                        : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </button>
                ))}
              </div>

              {tab === "overview" && <OverviewTab site={selectedSite} />}
              {tab === "performance" && <PerformanceTab siteId={selectedSite.id} siteUrl={selectedSite.base_url} />}
              {tab === "indexing" && <IndexingTab siteId={selectedSite.id} siteUrl={selectedSite.base_url} />}
              {tab === "social" && <SocialTab siteId={selectedSite.id} />}
              {tab === "blog" && <BlogTab siteId={selectedSite.id} />}
              {tab === "backlinks" && (
                <BacklinksTab siteId={selectedSite.id} siteName={selectedSite.name} siteUrl={selectedSite.base_url} />
              )}
            </>
          )
        )}
      </div>
    </>
  );
}
