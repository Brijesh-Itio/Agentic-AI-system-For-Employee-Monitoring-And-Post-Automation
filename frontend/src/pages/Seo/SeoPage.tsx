import { Fragment, FormEvent, ReactElement, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  AlertTriangle,
  ArrowUp,
  Award,
  BarChart3,
  CaseSensitive,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  ExternalLink,
  File,
  FileSearch,
  FileText,
  Folder,
  Hash,
  Gauge,
  Globe,
  History,
  Image as ImageIcon,
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
  TrendingDown,
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
  adoptSheets,
  applyTechnicalIssueFix,
  approveBlogPost,
  BlogPost,
  approveMetaRewrite,
  approveSocialPost,
  approveTechnicalIssue,
  BacklinkMention,
  checkPageSpeed,
  createSeoSite,
  analyzeContentStructure,
  DigestRollup,
  draftOutreachEmail,
  FaqPair,
  Ga4PageRow,
  generateBlogPost,
  generateBlogPostImage,
  generateDigestRollup,
  generateFaq,
  generateOgTags,
  generateSeoDigest,
  generateSocialPostImage,
  generateSocialPosts,
  generateTechnicalIssueAiSuggestion,
  generateTechnicalIssueFix,
  getTechnicalIssueEditTarget,
  getUrlEditTarget,
  runPageTagAudit,
  PageTagAuditReport,
  PageTagFinding,
  getBacklinks,
  getBlogPosts,
  getGa4Pages,
  getGscPages,
  getGscQueries,
  getIndexingSubmissions,
  getIndexStatusList,
  getMetaRewrites,
  getPageSpeedOpportunities,
  getPageSpeedResults,
  getRankAlerts,
  getSeoDigests,
  checkKeywordDifficulty,
  checkRapidApiKeywords,
  checkSemrushMetrics,
  getTopBacklinks,
  getDomainAuthority,
  getBulkDomainAuthority,
  getKeywordInsights,
  getWebsiteTraffic,
  getGscByCountry,
  getGscByDevice,
  getGscBySearchAppearance,
  getGscQueriesLive,
  getGscPagesLive,
  getGscTimeseries,
  GscFilterParams,
  GscDateRow,
  exportAllGscToSheet,
  getGa4PagesLive,
  getGa4BySource,
  getGa4ByCountry,
  getGa4ByDevice,
  getGa4Timeseries,
  getGa4Realtime,
  getGa4RealtimeByMinute,
  getGa4RealtimeByDevice,
  getGa4RealtimeByPage,
  getGa4RealtimeByAudience,
  getGa4Events,
  Ga4FilterParams,
  Ga4DateRow,
  exportAllGa4ToSheet,
  exportOverviewToSheet,
  getSitemaps,
  submitSitemap,
  deleteSitemap,
  getVerifiedSites,
  KeywordDifficulty,
  KeywordResearchRow,
  createServerFileBackup,
  deleteServerFile,
  getSemrushBacklinkGap,
  getSemrushBacklinks,
  getSemrushMetrics,
  getDigestRollups,
  getSemrushReferringDomains,
  getSeoJobs,
  getSeoSites,
  getSheetsStatus,
  SheetsKind,
  indexPageForInterlinks,
  getSocialPosts,
  updateSocialPost,
  getFacebookAccounts,
  createFacebookAccount,
  deleteFacebookAccount,
  FacebookAccount,
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
  GscPageRow,
  GscQueryRow,
  IndexingNotificationType,
  inspectUrl,
  MetaRewrite,
  OgTags,
  PageSpeedResult,
  PageSpeedStrategy,
  goLiveBlogPost,
  publishBlogPost,
  publishSocialPost,
  pullBacklinks,
  pullGscPages,
  RankChange,
  RelatedPage,
  rejectBlogPost,
  rejectMetaRewrite,
  updateBlogPost,
  updateBlogPostTaxonomy,
  uploadBlogPostImage,
  uploadSocialPostImage,
  rejectSocialPost,
  rejectTechnicalIssue,
  resolveTechnicalIssue,
  REMEDIABLE_RULES,
  DETERMINISTIC_FIX_RULES,
  researchKeywords,
  BulkConvertReport,
  runWebpConvertUrl,
  runTechnicalAudit,
  SeoJobRun,
  SeoSite,
  shareSheets,
  SocialPlatform,
  StructureIssue,
  StructureReport,
  submitForIndexing,
  suggestInterlinks,
  TechnicalIssue,
  updateSeoSiteCmsConfig,
  updateSeoSiteGoogleConfig,
  updateSeoSiteSshConfig,
} from "@/api";

type Tab = "overview" | "performance" | "search-console" | "analytics" | "indexing" | "social" | "blog" | "backlinks";
type IssueFilter = "pending" | "approved" | "rejected" | "resolved" | "all";

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
  resolved: "success",
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
  { id: "search-console", label: "Search Console", icon: Search },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "indexing", label: "Indexing", icon: FileSearch },
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
  // "published" only ever means "created as a draft in the CMS" — not
  // actually public yet, hence warning (needs the Go Live action) not
  // success. "live" is the one that's genuinely done.
  published: "warning",
  live: "success",
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

function ServerFileBrowser({
  site,
  jumpToPath,
  onJumpHandled,
}: {
  site: SeoSite;
  // Set by a "Mark as fixed manually" edit-target lookup elsewhere on
  // this page (a static file with no CMS post behind it) — opens that
  // exact file here instead of making the user navigate to it by hand.
  jumpToPath?: string | null;
  onJumpHandled?: () => void;
}) {
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

  useEffect(() => {
    if (!jumpToPath) return;
    goMutation.mutate(jumpToPath);
    onJumpHandled?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jumpToPath]);

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
    <Card id="server-file-browser">
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

// Closes two more blueprint gaps: Google Sheets ("live command centre")
// had no UI at all, and the weekly/monthly digest roll-up had no way to
// trigger or view it either.
// Module 39 — per-URL CMS image-to-WebP conversion. Paste a specific
// page's URL, it resolves to the actual CMS post behind it, finds any
// JPG/PNG <img src>/<img srcset> on that one page, converts each to
// WebP, uploads it alongside the original (nothing deleted), and
// rewrites just that page's content to point at the new file. Always
// dry-runs first (default here too) so the report can be reviewed
// before anything actually changes.
function WebpBulkConvertCard({ siteId }: { siteId: number }) {
  const toast = useToast();
  const [url, setUrl] = useState("");
  const [report, setReport] = useState<BulkConvertReport | null>(null);
  const [hasReviewedDryRun, setHasReviewedDryRun] = useState(false);

  const dryRunMutation = useMutation({
    mutationFn: () => runWebpConvertUrl(siteId, url.trim(), true),
    onSuccess: (data) => {
      setReport(data);
      setHasReviewedDryRun(true);
      if (data.error) toast.error(data.error);
      else toast.success(`Found ${data.images_found} image(s) on this page.`);
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Scan failed.")),
  });

  const runMutation = useMutation({
    mutationFn: () => runWebpConvertUrl(siteId, url.trim(), false),
    onSuccess: (data) => {
      setReport(data);
      setHasReviewedDryRun(false);
      if (data.error) toast.error(data.error);
      else toast.success(`Converted ${data.images_converted} image(s) on this page.`);
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Conversion failed.")),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <ImageIcon className="h-4 w-4 text-brand-500" />
          Convert Page Images to WebP
        </h2>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
          Paste a specific page's URL to convert its JPG/PNG images to WebP and rewrite that page's content to use
          them. Originals are never deleted, and the page is backed up first. Always scan (dry run) before
          converting for real.
        </p>
        <div className="flex flex-wrap gap-2">
          <Input
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setHasReviewedDryRun(false);
              setReport(null);
            }}
            placeholder="https://yoursite.com/some-page/"
            className="max-w-md"
          />
          <Button size="sm" variant="outline" onClick={() => dryRunMutation.mutate()} disabled={dryRunMutation.isPending || !url.trim()}>
            {dryRunMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
            Scan (dry run)
          </Button>
          <Button
            size="sm"
            onClick={() => {
              if (window.confirm("Convert images on this page for real? This uploads new WebP files and rewrites its content (originals are kept, and a backup is saved first).")) {
                runMutation.mutate();
              }
            }}
            disabled={runMutation.isPending || !hasReviewedDryRun}
          >
            {runMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Convert for real
          </Button>
        </div>
        {!hasReviewedDryRun && !runMutation.isPending && (
          <p className="mt-2 text-theme-xs text-gray-400">Scan this URL first — "Convert for real" unlocks once you've reviewed it.</p>
        )}
        {report && (
          <div className="mt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-md border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-theme-xs text-gray-400">Posts scanned</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">{report.posts_scanned}</p>
              </div>
              <div className="rounded-md border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-theme-xs text-gray-400">Images found</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">{report.images_found}</p>
              </div>
              <div className="rounded-md border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-theme-xs text-gray-400">{report.dry_run ? "Already converted" : "Converted"}</p>
                <p className="text-lg font-semibold text-success-600 dark:text-success-400">
                  {report.dry_run ? report.images_cached : report.images_converted}
                </p>
              </div>
              <div className="rounded-md border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-theme-xs text-gray-400">{report.dry_run ? "Posts affected" : "Posts updated"}</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {report.dry_run ? report.posts_with_images : report.posts_updated}
                </p>
              </div>
            </div>
            {report.images_failed > 0 && (
              <p className="text-theme-xs text-error-500">{report.images_failed} image(s) failed — see details below.</p>
            )}
            {report.details.length > 0 && (
              <ul className="space-y-1.5">
                {report.details.map((d) => (
                  <li key={d.post_id} className="rounded-md border border-gray-100 p-2 text-theme-xs dark:border-gray-800">
                    <span className="font-medium text-gray-700 dark:text-gray-300">{d.title}</span>{" "}
                    <span className="text-gray-400">
                      — {d.image_urls_found.length} image(s)
                      {!report.dry_run && d.updated && ", updated"}
                      {!report.dry_run && d.error && `, error: ${d.error}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

const TAG_BUCKET_STYLE: Record<
  "missing" | "existing" | "duplicate" | "invalid",
  { label: string; badge: "outline" | "success" | "warning" | "destructive"; icon: ReactElement }
> = {
  missing: { label: "Missing Tags", badge: "outline", icon: <XCircle className="h-3.5 w-3.5" /> },
  existing: { label: "Existing Tags", badge: "success", icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
  duplicate: { label: "Duplicate Tags", badge: "warning", icon: <AlertTriangle className="h-3.5 w-3.5" /> },
  invalid: { label: "Incorrect / Invalid Tags", badge: "destructive", icon: <AlertTriangle className="h-3.5 w-3.5" /> },
};

function TagFindingGroup({
  kind,
  findings,
}: {
  kind: "missing" | "existing" | "duplicate" | "invalid";
  findings: PageTagFinding[];
}) {
  const style = TAG_BUCKET_STYLE[kind];
  return (
    <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
      <div className="mb-2 flex items-center gap-2">
        <Badge variant={style.badge}>
          {style.icon}
          {style.label}
        </Badge>
        <span className="text-theme-xs text-gray-400">{findings.length}</span>
      </div>
      {findings.length === 0 ? (
        <p className="text-theme-xs text-gray-400">None.</p>
      ) : (
        <ul className="space-y-2">
          {findings.map((f) => (
            <li key={f.tag} className="text-theme-xs">
              <span className="font-medium text-gray-700 dark:text-gray-300">{f.tag}</span>
              <span className="text-gray-400"> — {f.detail}</span>
              {f.values.length > 0 && (
                <div className="mt-0.5 space-y-0.5">
                  {f.values.map((v, i) => (
                    <p key={i} className="break-all text-gray-500 dark:text-gray-400">
                      {v || <em>(empty)</em>}
                    </p>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PageTagAuditCard({ siteId }: { siteId: number }) {
  const toast = useToast();
  const [url, setUrl] = useState("");
  const [report, setReport] = useState<PageTagAuditReport | null>(null);

  const auditMutation = useMutation({
    mutationFn: () => runPageTagAudit(siteId, url.trim()),
    onSuccess: (result) => {
      setReport(result);
      toast.success(`Tag audit complete for ${result.url}.`);
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Could not audit this page — see server logs.");
    },
  });

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <FileSearch className="h-4 w-4 text-brand-500" />
          Run Technical Audit — Individual Page
        </h2>
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          Check one page's own SEO tags — title, meta description, canonical, robots, viewport, Open Graph, Twitter
          Card, structured data, H1 — and report which are missing, present, duplicated, or invalid.
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://yoursite.com/some-page/"
            className="max-w-md"
          />
          <Button onClick={() => auditMutation.mutate()} disabled={auditMutation.isPending || !url.trim()}>
            {auditMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />}
            Run Technical Audit (Page)
          </Button>
        </div>

        {report && (
          <div className="mt-4 space-y-3">
            <p className="break-all text-theme-xs text-gray-400">{report.url}</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TagFindingGroup kind="missing" findings={report.missing_tags} />
              <TagFindingGroup kind="existing" findings={report.existing_tags} />
              <TagFindingGroup kind="duplicate" findings={report.duplicate_tags} />
              <TagFindingGroup kind="invalid" findings={report.invalid_tags} />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Module 56/57 — one of the separate "Export to Sheets" destinations
// (main pipeline log / Search Console / Analytics / Overview report),
// each its own spreadsheet a human adopts independently. Previously
// ReportingPanel rendered a single hardcoded card for what was one
// shared spreadsheet; now it renders one instance of this per
// SheetsKind, each with fully independent connect/status/share state so
// connecting one never touches another's.
function SheetsConnectCard({ kind, title, description }: { kind: SheetsKind; title: string; description: ReactElement | string }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [shareEmail, setShareEmail] = useState("");
  const [sheetUrl, setSheetUrl] = useState("");

  // A useQuery, not a mutation fired only on button click — the
  // connection is a real, server-persisted setting (app_settings), so it
  // must survive a page refresh instead of resetting to "not connected"
  // every time this component remounts. Silent on the automatic mount
  // fetch (an unconfigured sheet isn't an error worth a toast on every
  // page load); the explicit "Refresh" click below still reports it.
  const sheetsQuery = useQuery({
    queryKey: ["seo", "sheets-status", kind],
    queryFn: () => getSheetsStatus(kind),
    retry: false,
  });
  const sheets = sheetsQuery.data ?? null;

  const refreshSheetsStatus = async () => {
    const result = await queryClient.fetchQuery({ queryKey: ["seo", "sheets-status", kind], queryFn: () => getSheetsStatus(kind) });
    if (!result.configured) toast.error(result.error || "Sheet not configured yet.");
  };

  const shareMutation = useMutation({
    mutationFn: () => shareSheets(shareEmail.trim(), kind),
    onSuccess: (data) => {
      queryClient.setQueryData(["seo", "sheets-status", kind], data);
      if (data.configured) toast.success(`Shared with ${shareEmail.trim()}.`);
      else toast.error(data.error || "Sharing failed.");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Sharing failed.")),
  });

  // Service accounts created after April 2025 have zero Drive storage
  // quota and can't create their own spreadsheet — this is the real
  // path: paste a sheet you created yourself and shared with the
  // service account as Editor.
  const adoptMutation = useMutation({
    mutationFn: () => adoptSheets(sheetUrl.trim(), kind),
    onSuccess: (data) => {
      queryClient.setQueryData(["seo", "sheets-status", kind], data);
      if (data.configured) toast.success("Connected — tabs and headers set up.");
      else toast.error(data.error || "Could not connect to that sheet.");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Could not connect to that sheet.")),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <History className="h-4 w-4 text-brand-500" />
          {title}
        </h2>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">{description}</p>
        <div className="mb-3 flex flex-wrap gap-2">
          <Input
            value={sheetUrl}
            onChange={(e) => setSheetUrl(e.target.value)}
            placeholder="Paste your Google Sheet URL or ID"
            className="max-w-sm"
          />
          <Button size="sm" onClick={() => adoptMutation.mutate()} disabled={adoptMutation.isPending || !sheetUrl.trim()}>
            {adoptMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Connect
          </Button>
        </div>
        <Button size="sm" variant="outline" onClick={() => refreshSheetsStatus()} disabled={sheetsQuery.isFetching}>
          {sheetsQuery.isFetching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          {sheets?.configured ? "Refresh" : "Check status"}
        </Button>
        {sheets?.configured && sheets.url && (
          <a
            href={sheets.url}
            target="_blank"
            rel="noreferrer"
            className="ml-2 text-theme-sm text-brand-600 underline dark:text-brand-400"
          >
            Open spreadsheet
          </a>
        )}
        {sheets && !sheets.configured && (
          <p className="mt-2 text-theme-xs text-error-500">{sheets.error}</p>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          <Input
            value={shareEmail}
            onChange={(e) => setShareEmail(e.target.value)}
            placeholder="Share with a different Google account email"
            className="max-w-xs"
          />
          <Button
            size="sm"
            variant="outline"
            onClick={() => shareMutation.mutate()}
            disabled={shareMutation.isPending || !shareEmail.trim()}
          >
            {shareMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Share
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ReportingPanel({ siteId }: { siteId: number }) {
  const toast = useToast();
  const [rollupPeriod, setRollupPeriod] = useState<DigestRollupPeriod>("weekly");
  const [rollup, setRollup] = useState<DigestRollup | null>(null);
  // Module 58 — referenceDate anchors weekly/monthly to a chosen past
  // day instead of always literal today; customStart/customEnd are a
  // genuinely arbitrary range, only used when rollupPeriod === "custom".
  const [referenceDate, setReferenceDate] = useState("");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [rollupEmailAddr, setRollupEmailAddr] = useState("");

  const rollupsQuery = useQuery({
    queryKey: ["seo", "digest-rollups", siteId, rollupPeriod],
    queryFn: () => getDigestRollups(siteId, rollupPeriod),
  });
  const latestSaved = rollupsQuery.data?.[0] ?? null;

  const customRangeReady = rollupPeriod !== "custom" || (!!customStart && !!customEnd);
  const rollupOpts = () => ({
    referenceDate: rollupPeriod !== "custom" ? referenceDate || null : null,
    startDate: rollupPeriod === "custom" ? customStart || null : null,
    endDate: rollupPeriod === "custom" ? customEnd || null : null,
  });

  const rollupMutation = useMutation({
    mutationFn: () => generateDigestRollup(siteId, rollupPeriod, rollupOpts()),
    onSuccess: (data) => {
      setRollup(data);
      toast.success(`${rollupPeriod === "weekly" ? "Weekly" : rollupPeriod === "monthly" ? "Monthly" : "Custom"} roll-up generated.`);
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Roll-up generation failed.")),
  });

  // Module 58 — export/share was previously Slack + a Sheets tab only;
  // reuses the same Gmail sender already live for DAR/alert email.
  const rollupEmailMutation = useMutation({
    mutationFn: () => generateDigestRollup(siteId, rollupPeriod, { ...rollupOpts(), sendEmail: true, emailRecipient: rollupEmailAddr || null }),
    onSuccess: (data) => {
      setRollup(data);
      if (data.emailed_at) toast.success(`Roll-up emailed${rollupEmailAddr ? ` to ${rollupEmailAddr}` : ""}.`);
      else toast.error("Roll-up generated but the email failed — check GMAIL_ADDRESS/GMAIL_APP_PASSWORD in .env.");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Email failed.")),
  });

  const shown = rollup ?? latestSaved;

  const downloadRollup = () => {
    if (!shown) return;
    const blob = new Blob(
      [`SEO ${shown.period} roll-up — ${shown.period_start} to ${shown.period_end}\n\n${shown.narrative}`],
      { type: "text/plain;charset=utf-8;" }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `seo-rollup-${shown.period}-${shown.period_start}-to-${shown.period_end}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };
  const serviceAccountLine = (
    <>
      Google gives service accounts no Drive storage of their own, so create a blank sheet yourself, share it with{" "}
      <span className="font-mono">workpulse-seo-agent@workpulse-ai-506706.iam.gserviceaccount.com</span> as Editor, and
      paste its link below — the app sets up the tabs for you.
    </>
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-4">
        <SheetsConnectCard
          kind="main"
          title="Pipeline sheet"
          description={<>The daily pipeline's own logs (rank/CWV/content/issue/link/digest). {serviceAccountLine}</>}
        />
        <SheetsConnectCard
          kind="gsc"
          title="Search Console sheet"
          description={<>Everything exported from the Search Console Performance dashboard. {serviceAccountLine}</>}
        />
        <SheetsConnectCard
          kind="ga4"
          title="Analytics sheet"
          description={<>Everything exported from the Analytics Performance dashboard, including Events. {serviceAccountLine}</>}
        />
        <SheetsConnectCard
          kind="overview"
          title="Overview report sheet"
          description={<>The Overview dashboard's own report (Top Queries/Pages/CTR by Page/Rank Alerts). {serviceAccountLine}</>}
        />
      </div>

      <Card>
        <CardContent className="p-6">
          <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <Sparkles className="h-4 w-4 text-brand-500" />
            Weekly / monthly roll-up
          </h2>
          <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
            Trend summary across this period's daily digests. Also runs automatically (Monday mornings / 1st of
            month).
          </p>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Button size="sm" variant={rollupPeriod === "weekly" ? "default" : "outline"} onClick={() => { setRollupPeriod("weekly"); setRollup(null); }}>
              Weekly
            </Button>
            <Button size="sm" variant={rollupPeriod === "monthly" ? "default" : "outline"} onClick={() => { setRollupPeriod("monthly"); setRollup(null); }}>
              Monthly
            </Button>
            <Button size="sm" variant={rollupPeriod === "custom" ? "default" : "outline"} onClick={() => { setRollupPeriod("custom"); setRollup(null); }}>
              Custom
            </Button>
            {rollupPeriod === "custom" ? (
              <>
                <Input type="date" value={customStart} onChange={(e) => setCustomStart(e.target.value)} className="max-w-40" />
                <span className="text-theme-xs text-gray-400">to</span>
                <Input type="date" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} className="max-w-40" />
              </>
            ) : (
              <Input
                type="date"
                value={referenceDate}
                onChange={(e) => setReferenceDate(e.target.value)}
                className="max-w-40"
                title={`Pull a specific past ${rollupPeriod === "weekly" ? "week's" : "month's"} report instead of the current one`}
              />
            )}
            <Button size="sm" onClick={() => rollupMutation.mutate()} disabled={rollupMutation.isPending || !customRangeReady}>
              {rollupMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              Generate now
            </Button>
          </div>
          {rollupsQuery.isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
          ) : shown ? (
            <>
              <p className="whitespace-pre-line text-theme-sm text-gray-700 dark:text-gray-300">{shown.narrative}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {shown.emailed_at && <Badge variant="success">Emailed</Badge>}
                <Button size="sm" variant="outline" onClick={downloadRollup}>
                  <Download className="h-3.5 w-3.5" />
                  Download
                </Button>
                <Input
                  value={rollupEmailAddr}
                  onChange={(e) => setRollupEmailAddr(e.target.value)}
                  placeholder="Email address (optional)"
                  className="max-w-52"
                />
                <Button size="sm" variant="outline" onClick={() => rollupEmailMutation.mutate()} disabled={rollupEmailMutation.isPending || !customRangeReady}>
                  {rollupEmailMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}
                  Email
                </Button>
              </div>
            </>
          ) : (
            <p className="text-theme-sm text-gray-400">No roll-up generated yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function OverviewTab({
  site,
  serverJumpPath,
  onServerJumpHandled,
  onEditStaticFile,
}: {
  site: SeoSite;
  // Set by the parent SeoPage when "Edit this page"/"Edit this file"
  // (here, or from the PageSpeed tab) resolves to a static file with no
  // CMS post behind it — jumps the Server Files browser further down
  // this same page straight to that file instead of leaving the user to
  // find it.
  serverJumpPath: string | null;
  onServerJumpHandled: () => void;
  onEditStaticFile: (path: string) => void;
}) {
  const siteId = site.id;
  const queryClient = useQueryClient();
  const toast = useToast();
  const [issueFilter, setIssueFilter] = useState<IssueFilter>("pending");
  const [digestRunDate, setDigestRunDate] = useState("");
  const [digestEmailAddr, setDigestEmailAddr] = useState("");

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
    mutationFn: () => generateSeoDigest(siteId, { runDate: digestRunDate || null }),
    onSuccess: () => {
      toast.success(digestRunDate ? `Digest generated for ${digestRunDate}.` : "Digest generated.");
      queryClient.invalidateQueries({ queryKey: ["seo", "digests", siteId] });
    },
    onError: () => toast.error("Digest generation failed — check that Ollama is running."),
  });

  // Module 58 — export/share was previously Slack + a Sheets tab only;
  // this reuses the same Gmail sender already live for DAR/alert email
  // instead of building a second one. Regenerates (same as "Generate
  // Digest" above) rather than re-sending a stale cached narrative.
  const digestEmailMutation = useMutation({
    mutationFn: () => generateSeoDigest(siteId, { runDate: digestRunDate || null, sendEmail: true, emailRecipient: digestEmailAddr || null }),
    onSuccess: (data) => {
      if (data.emailed_at) toast.success(`Digest emailed${digestEmailAddr ? ` to ${digestEmailAddr}` : ""}.`);
      else toast.error("Digest generated but the email failed — check GMAIL_ADDRESS/GMAIL_APP_PASSWORD in .env.");
      queryClient.invalidateQueries({ queryKey: ["seo", "digests", siteId] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Email failed.")),
  });

  const downloadDigest = () => {
    if (!latestDigest) return;
    const blob = new Blob([`SEO Digest — ${site.name} (${latestDigest.run_date})\n\n${latestDigest.narrative}`], {
      type: "text/plain;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `seo-digest-${site.name.replace(/[^a-z0-9]+/gi, "-")}-${latestDigest.run_date}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const approveMutation = useMutation({
    mutationFn: (issueId: number) => approveTechnicalIssue(issueId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "issues", siteId] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (issueId: number) => rejectTechnicalIssue(issueId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "issues", siteId] }),
  });

  const resolveMutation = useMutation({
    mutationFn: (issueId: number) => resolveTechnicalIssue(issueId),
    onSuccess: () => {
      toast.success("Marked as fixed.");
      queryClient.invalidateQueries({ queryKey: ["seo", "issues", siteId] });
    },
  });

  const editTargetMutation = useMutation({
    mutationFn: (issueId: number) => getTechnicalIssueEditTarget(issueId),
    onSuccess: (target) => {
      if (target.kind === "cms" && target.edit_url) {
        window.open(target.edit_url, "_blank", "noopener,noreferrer");
      } else if (target.kind === "static_file" && target.file_path) {
        onEditStaticFile(target.file_path);
        document.getElementById("server-file-browser")?.scrollIntoView({ behavior: "smooth", block: "start" });
      } else {
        toast.error(target.detail);
      }
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Could not resolve where to edit this issue.");
    },
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

  const aiSuggestionMutation = useMutation({
    mutationFn: (issueId: number) => generateTechnicalIssueAiSuggestion(issueId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "issues", siteId] }),
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Could not generate an AI suggestion for this issue.");
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

      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => auditMutation.mutate()} disabled={auditMutation.isPending}>
          {auditMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Run Technical Audit
        </Button>
        <Button variant="outline" onClick={() => digestMutation.mutate()} disabled={digestMutation.isPending}>
          {digestMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Generate Digest
        </Button>
        <Input
          type="date"
          value={digestRunDate}
          onChange={(e) => setDigestRunDate(e.target.value)}
          className="max-w-40"
          title="Backfill a specific past day instead of today"
        />
      </div>

      <PageTagAuditCard siteId={siteId} />

      <Card>
        <CardContent className="p-6">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
              <Sparkles className="h-4 w-4 text-brand-500" />
              Latest Digest
            </h2>
            {latestDigest && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-theme-xs text-gray-400">{latestDigest.run_date}</span>
                <Badge variant={latestDigest.slack_delivered ? "success" : "outline"}>
                  {latestDigest.slack_delivered ? "Sent to Slack" : "Not sent to Slack"}
                </Badge>
                {latestDigest.emailed_at && <Badge variant="success">Emailed</Badge>}
                <Button size="sm" variant="outline" onClick={downloadDigest}>
                  <Download className="h-3.5 w-3.5" />
                  Download
                </Button>
                <Input
                  value={digestEmailAddr}
                  onChange={(e) => setDigestEmailAddr(e.target.value)}
                  placeholder="Email address (optional)"
                  className="max-w-52"
                />
                <Button size="sm" variant="outline" onClick={() => digestEmailMutation.mutate()} disabled={digestEmailMutation.isPending}>
                  {digestEmailMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}
                  Email
                </Button>
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

      <OverviewExportBar siteId={siteId} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SearchConsolePanel siteId={siteId} />
        <AnalyticsPanel siteId={siteId} />
        <PageCtrPanel siteId={siteId} />
        <RankAlertsPanel siteId={siteId} />
      </div>

      <MetaRewriteQueuePanel siteId={siteId} />

      <ReportingPanel siteId={siteId} />

      <WebpBulkConvertCard siteId={siteId} />

      <JobHistoryPanel jobs={jobs} loading={jobsQuery.isLoading} />

      <Card>
        <CardContent className="p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
              <AlertTriangle className="h-4 w-4 text-brand-500" />
              Technical Issues
            </h2>
            <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-white/5">
              {(["pending", "approved", "rejected", "resolved", "all"] as IssueFilter[]).map((f) => (
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

                  <div className="mt-2 rounded-md border border-dashed border-gray-200 p-3 dark:border-gray-700">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="flex items-center gap-1 text-theme-xs font-medium text-gray-500 dark:text-gray-400">
                        <Sparkles className="h-3.5 w-3.5 text-brand-500" />
                        Ollama suggestion
                      </p>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => aiSuggestionMutation.mutate(issue.id)}
                        disabled={aiSuggestionMutation.isPending}
                      >
                        {aiSuggestionMutation.isPending ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Sparkles className="h-3.5 w-3.5" />
                        )}
                        {issue.ai_suggestion ? "Regenerate suggestion" : "Get AI suggestion"}
                      </Button>
                    </div>
                    {issue.ai_suggestion && (
                      <p className="mt-2 whitespace-pre-line text-theme-sm text-gray-700 dark:text-gray-300">
                        {issue.ai_suggestion}
                      </p>
                    )}
                  </div>

                  {REMEDIABLE_RULES.includes(issue.rule) || DETERMINISTIC_FIX_RULES.includes(issue.rule) ? (
                    <div className="mt-3 rounded-md bg-gray-50 p-3 dark:bg-white/5">
                      {issue.fix_value ? (
                        <>
                          <p className="text-theme-xs font-medium text-gray-500 dark:text-gray-400">
                            {issue.fix_applied
                              ? "Applied to the live site:"
                              : REMEDIABLE_RULES.includes(issue.rule)
                                ? "Ready to apply:"
                                : "Exact fix — copy this into your CMS/theme:"}
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
                        <div className="mt-2 flex flex-wrap items-center gap-2">
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
                          {issue.fix_value && REMEDIABLE_RULES.includes(issue.rule) && issue.status === "approved" && (
                            <Button size="sm" onClick={() => applyFixMutation.mutate(issue.id)} disabled={applyFixMutation.isPending}>
                              {applyFixMutation.isPending ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Send className="h-3.5 w-3.5" />
                              )}
                              Apply to website
                            </Button>
                          )}
                          {issue.fix_value && REMEDIABLE_RULES.includes(issue.rule) && issue.status !== "approved" && (
                            <span className="self-center text-theme-xs text-gray-400">Approve this issue to apply the fix</span>
                          )}
                          {issue.fix_value && DETERMINISTIC_FIX_RULES.includes(issue.rule) && (
                            <span className="self-center text-theme-xs text-gray-400">
                              No CMS field to write this to automatically — paste it in yourself, then mark it fixed below.
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="mt-2 text-theme-xs text-gray-400">
                      Structural issue — no exact auto-generated value. Use the Ollama suggestion above, fix it in your
                      CMS/theme, then mark it fixed below.
                    </p>
                  )}

                  <div className="mt-3 flex flex-wrap gap-2">
                    {issue.status === "pending" && (
                      <>
                        <Button size="sm" variant="outline" onClick={() => approveMutation.mutate(issue.id)}>
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Approve
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => rejectMutation.mutate(issue.id)}>
                          <XCircle className="h-3.5 w-3.5" />
                          Reject
                        </Button>
                      </>
                    )}
                    {(issue.status === "pending" || issue.status === "approved") && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => editTargetMutation.mutate(issue.id)}
                          disabled={editTargetMutation.isPending}
                        >
                          {editTargetMutation.isPending ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <ExternalLink className="h-3.5 w-3.5" />
                          )}
                          Edit this page
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => resolveMutation.mutate(issue.id)}
                          disabled={resolveMutation.isPending}
                        >
                          {resolveMutation.isPending ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          )}
                          Mark as fixed manually
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <GoogleConfigCard site={site} />
      <CmsConfigCard site={site} />
      <ServerAccessConfigCard site={site} />
      <ServerFileBrowser site={site} jumpToPath={serverJumpPath} onJumpHandled={onServerJumpHandled} />
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

function OverviewExportBar({ siteId }: { siteId: number }) {
  const toast = useToast();
  // Same query keys/queryFns each of the 4 panels below already uses —
  // React Query dedupes on the key, so this shares their cache rather
  // than re-fetching, and always exports whatever's actually on screen.
  const queriesQuery = useQuery({ queryKey: ["seo", "gsc", siteId], queryFn: () => getGscQueries(siteId, 8) });
  const pagesQuery = useQuery({ queryKey: ["seo", "ga4", siteId], queryFn: () => getGa4Pages(siteId, 8) });
  const ctrQuery = useQuery({ queryKey: ["seo", "gsc-pages", siteId], queryFn: () => getGscPages(siteId, 10) });
  const rankQuery = useQuery({ queryKey: ["seo", "rank-alerts", siteId], queryFn: () => getRankAlerts(siteId) });

  const hasAnyData =
    (queriesQuery.data?.length ?? 0) > 0 ||
    (pagesQuery.data?.length ?? 0) > 0 ||
    (ctrQuery.data?.length ?? 0) > 0 ||
    (rankQuery.data?.length ?? 0) > 0;

  const exportMutation = useMutation({
    mutationFn: () =>
      exportOverviewToSheet(siteId, {
        top_queries: queriesQuery.data ?? [],
        top_pages: pagesQuery.data ?? [],
        ctr_by_page: ctrQuery.data ?? [],
        rank_alerts: rankQuery.data ?? [],
      }),
    onSuccess: (result) => {
      if (!result.ok) {
        toast.error(result.detail);
        return;
      }
      toast.success(result.detail);
      if (result.sheet_url) window.open(result.sheet_url, "_blank", "noopener,noreferrer");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Export to Sheets failed.")),
  });

  const downloadCsv = () => {
    const escape = (cell: string) => `"${cell.replace(/"/g, '""')}"`;
    const section = (title: string, header: string[], rows: string[][]) =>
      [
        escape(title),
        header.map(escape).join(","),
        ...(rows.length ? rows.map((row) => row.map(escape).join(",")) : [escape("(no rows)")]),
      ].join("\r\n");

    const csv = [
      section(
        "Top Search Queries",
        ["Query", "Clicks", "Impressions", "CTR", "Avg. Position"],
        (queriesQuery.data ?? []).map((r) => [
          r.query,
          String(r.clicks),
          String(r.impressions),
          r.ctr != null ? `${(r.ctr * 100).toFixed(2)}%` : "",
          r.position != null ? r.position.toFixed(1) : "",
        ])
      ),
      section(
        "Top Traffic Pages",
        ["Page", "Sessions", "Bounce Rate", "Conversions"],
        (pagesQuery.data ?? []).map((r) => [
          r.page_path,
          String(r.sessions),
          r.bounce_rate != null ? `${(r.bounce_rate * 100).toFixed(2)}%` : "",
          r.conversions != null ? String(r.conversions) : "",
        ])
      ),
      section(
        "CTR by Page",
        ["Page", "Clicks", "Impressions", "CTR", "Avg. Position"],
        (ctrQuery.data ?? []).map((r) => [
          r.page,
          String(r.clicks),
          String(r.impressions),
          r.ctr != null ? `${(r.ctr * 100).toFixed(2)}%` : "",
          r.position != null ? r.position.toFixed(1) : "",
        ])
      ),
      section(
        "Rank Alerts",
        ["Query", "Previous Position", "Current Position", "Delta"],
        (rankQuery.data ?? []).map((r) => [r.query, r.previous_position.toFixed(1), r.current_position.toFixed(1), r.delta.toFixed(1)])
      ),
    ].join("\r\n\r\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `overview-report-site-${siteId}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!hasAnyData) return null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h2 className="flex items-center gap-2 text-base font-semibold text-gray-900 dark:text-white">
        <LayoutDashboard className="h-4 w-4 text-brand-500" />
        Overview Report
      </h2>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={downloadCsv}>
          <Download className="h-3.5 w-3.5" />
          Download CSV
        </Button>
        <Button size="sm" variant="outline" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
          {exportMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
          Export to Sheets
        </Button>
      </div>
    </div>
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
                  {row.clicks} clicks · {row.impressions} impr. ·{" "}
                  {row.ctr != null ? `${(row.ctr * 100).toFixed(1)}% CTR` : "—"} · pos{" "}
                  {row.position != null ? row.position.toFixed(1) : "—"}
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

function PageCtrPanel({ siteId }: { siteId: number }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const query = useQuery({ queryKey: ["seo", "gsc-pages", siteId], queryFn: () => getGscPages(siteId, 10) });
  const rows = query.data ?? [];

  const pullMutation = useMutation({
    mutationFn: () => pullGscPages(siteId, 28),
    onSuccess: () => {
      toast.success("Pulled page-level Search Console data.");
      queryClient.invalidateQueries({ queryKey: ["seo", "gsc-pages", siteId] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "GSC page pull failed — check GSC_SITE_URL/service account access.")),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <BarChart3 className="h-4 w-4 text-brand-500" />
            CTR by Page
          </h2>
          <Button size="sm" variant="outline" onClick={() => pullMutation.mutate()} disabled={pullMutation.isPending}>
            {pullMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Pull now
          </Button>
        </div>
        {query.isLoading ? (
          <div className="flex h-20 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : rows.length === 0 ? (
          <p className="text-theme-sm text-gray-400">
            No page-level Search Console data yet — click "Pull now" or wait for the daily automated cycle.
          </p>
        ) : (
          <div className="space-y-2">
            {rows.map((row: GscPageRow) => (
              <div key={row.id} className="flex items-center justify-between gap-3 text-theme-sm">
                <span className="truncate text-gray-700 dark:text-gray-300">{row.page}</span>
                <span className="shrink-0 text-theme-xs text-gray-400">
                  {row.clicks} clicks · {row.impressions} impr. ·{" "}
                  {row.ctr != null ? `${(row.ctr * 100).toFixed(1)}% CTR` : "—"} · pos{" "}
                  {row.position != null ? row.position.toFixed(1) : "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RankAlertsPanel({ siteId }: { siteId: number }) {
  const query = useQuery({ queryKey: ["seo", "rank-alerts", siteId], queryFn: () => getRankAlerts(siteId) });
  const changes = query.data ?? [];
  const drops = changes.filter((c) => c.previous_position <= 10 && c.current_position > 10);

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <TrendingDown className="h-4 w-4 text-brand-500" />
          Rank Alerts
        </h2>
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          Position changes vs. the last Search Console pull.
        </p>
        {query.isLoading ? (
          <div className="flex h-20 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : changes.length === 0 ? (
          <p className="text-theme-sm text-gray-400">
            Not enough data yet — needs at least two days of pulled Search Console data to compare.
          </p>
        ) : (
          <div className="space-y-2">
            {drops.length > 0 && (
              <div className="mb-3 space-y-2">
                {drops.map((c: RankChange) => (
                  <div
                    key={`drop-${c.query}`}
                    className="flex items-center justify-between gap-3 rounded-lg border border-error-200 bg-error-50 p-3 text-theme-sm dark:border-error-500/30 dark:bg-error-500/10"
                  >
                    <span className="truncate text-gray-800 dark:text-gray-200">{c.query}</span>
                    <Badge variant="destructive">
                      fell out of top 10 ({c.previous_position.toFixed(0)} → {c.current_position.toFixed(0)})
                    </Badge>
                  </div>
                ))}
              </div>
            )}
            {changes
              .filter((c) => !drops.includes(c))
              .map((c: RankChange) => (
                <div key={c.query} className="flex items-center justify-between gap-3 text-theme-sm">
                  <span className="truncate text-gray-700 dark:text-gray-300">{c.query}</span>
                  <span className="shrink-0 flex items-center gap-1 text-theme-xs text-gray-400">
                    {c.delta < 0 ? (
                      <TrendingUp className="h-3.5 w-3.5 text-success-500" />
                    ) : c.delta > 0 ? (
                      <TrendingDown className="h-3.5 w-3.5 text-warning-500" />
                    ) : null}
                    {c.previous_position.toFixed(0)} → {c.current_position.toFixed(0)}
                  </span>
                </div>
              ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

const metaRewriteStatusVariant: Record<string, "warning" | "success" | "outline"> = {
  queued: "warning",
  approved: "success",
  rejected: "outline",
};

function MetaRewriteQueuePanel({ siteId }: { siteId: number }) {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["seo", "meta-rewrites", siteId], queryFn: () => getMetaRewrites(siteId) });
  const items = query.data ?? [];

  const approveMutation = useMutation({
    mutationFn: (id: number) => approveMetaRewrite(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "meta-rewrites", siteId] }),
  });
  const rejectMutation = useMutation({
    mutationFn: (id: number) => rejectMetaRewrite(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seo", "meta-rewrites", siteId] }),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Sparkles className="h-4 w-4 text-brand-500" />
          Meta Rewrite Opportunities
        </h2>
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          Pages with real search demand (high impressions) but a snippet that isn't earning clicks (low CTR) —
          AI-drafted rewrites, never auto-published. Review and apply the ones you approve manually.
        </p>
        {query.isLoading ? (
          <div className="flex h-20 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <p className="text-theme-sm text-gray-400">
            No opportunities queued yet — found automatically once a page has enough impressions and low enough CTR
            during the daily cycle.
          </p>
        ) : (
          <div className="space-y-3">
            {items.map((item: MetaRewrite) => (
              <div key={item.id} className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={metaRewriteStatusVariant[item.status] ?? "outline"}>{item.status}</Badge>
                  <span className="text-theme-xs text-gray-400">
                    {item.impressions} impr. · {item.clicks} clicks ·{" "}
                    {item.ctr != null ? `${(item.ctr * 100).toFixed(1)}% CTR` : "—"} · pos{" "}
                    {item.position != null ? item.position.toFixed(1) : "—"}
                  </span>
                </div>
                <p className="mt-2 break-all text-theme-sm font-medium text-gray-900 dark:text-white">{item.url}</p>
                {item.suggested_title ? (
                  <div className="mt-2 space-y-1">
                    <p className="text-theme-sm text-gray-700 dark:text-gray-300">
                      <span className="text-gray-400">Suggested title: </span>
                      {item.suggested_title}
                    </p>
                    <p className="text-theme-sm text-gray-700 dark:text-gray-300">
                      <span className="text-gray-400">Suggested description: </span>
                      {item.suggested_description}
                    </p>
                  </div>
                ) : (
                  <p className="mt-2 text-theme-xs text-gray-400">No AI draft yet for this item.</p>
                )}
                {item.status === "queued" && (
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => approveMutation.mutate(item.id)}>
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Approve
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => rejectMutation.mutate(item.id)}>
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
  );
}

function SocialTab({ siteId }: { siteId: number }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [pageTitle, setPageTitle] = useState("");
  const [contentExcerpt, setContentExcerpt] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<SocialPlatform[]>(["linkedin"]);
  const [facebookAccountId, setFacebookAccountId] = useState<number | "">("");

  const postsQuery = useQuery({ queryKey: ["seo", "social", siteId], queryFn: () => getSocialPosts(siteId) });
  const posts = postsQuery.data ?? [];

  // Module 40 — multiple connected Facebook Pages. Global (not scoped to
  // this site) since a Page is Meta's own asset, not tied to one SEO
  // site; posts for any site can publish through any connected account.
  const facebookAccountsQuery = useQuery({ queryKey: ["seo", "facebook-accounts"], queryFn: getFacebookAccounts });
  const facebookAccounts = facebookAccountsQuery.data ?? [];

  const generateMutation = useMutation({
    mutationFn: () =>
      generateSocialPosts({
        site_id: siteId,
        page_title: pageTitle,
        content_excerpt: contentExcerpt,
        image_url: imageUrl.trim() || undefined,
        platforms: selectedPlatforms,
        facebook_account_id: facebookAccountId === "" ? undefined : facebookAccountId,
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

  const [editingPostId, setEditingPostId] = useState<number | null>(null);
  const [editedContent, setEditedContent] = useState("");
  const updateMutation = useMutation({
    mutationFn: ({ id, content }: { id: number; content: string }) => updateSocialPost(id, content),
    onSuccess: () => {
      toast.success("Post updated.");
      setEditingPostId(null);
      queryClient.invalidateQueries({ queryKey: ["seo", "social", siteId] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Couldn't save this edit.")),
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

  // Instagram has no text-only post type — this is what actually lets
  // an Instagram draft become publishable, without requiring a human to
  // hand-paste an image URL from somewhere else first.
  const imageMutation = useMutation({
    mutationFn: (id: number) => generateSocialPostImage(id),
    onSuccess: () => {
      toast.success("Image generated and uploaded to the site.");
      queryClient.invalidateQueries({ queryKey: ["seo", "social", siteId] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Image generation failed.")),
  });

  const uploadImageMutation = useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => uploadSocialPostImage(id, file),
    onSuccess: () => {
      toast.success("Image uploaded to the site.");
      queryClient.invalidateQueries({ queryKey: ["seo", "social", siteId] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Image upload failed.")),
  });
  const uploadInputRefs = useRef<Record<number, HTMLInputElement | null>>({});

  const togglePlatform = (p: SocialPlatform) => {
    setSelectedPlatforms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));
  };

  const [showAddAccount, setShowAddAccount] = useState(false);
  const [newAccountLabel, setNewAccountLabel] = useState("");
  const [newAccountPageId, setNewAccountPageId] = useState("");
  const [newAccountToken, setNewAccountToken] = useState("");

  const createAccountMutation = useMutation({
    mutationFn: () =>
      createFacebookAccount({ label: newAccountLabel.trim(), page_id: newAccountPageId.trim(), page_access_token: newAccountToken.trim() }),
    onSuccess: () => {
      toast.success("Facebook account added.");
      setNewAccountLabel("");
      setNewAccountPageId("");
      setNewAccountToken("");
      setShowAddAccount(false);
      queryClient.invalidateQueries({ queryKey: ["seo", "facebook-accounts"] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Couldn't add this Facebook account.")),
  });

  const deleteAccountMutation = useMutation({
    mutationFn: (id: number) => deleteFacebookAccount(id),
    onSuccess: () => {
      toast.success("Facebook account removed.");
      queryClient.invalidateQueries({ queryKey: ["seo", "facebook-accounts"] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Couldn't remove this Facebook account.")),
  });

  return (
    <>
      {selectedPlatforms.includes("facebook") && (
        <Card>
          <CardContent className="p-6">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
              <FacebookIcon className="h-4 w-4 text-brand-500" />
              Facebook accounts
            </h2>
            {facebookAccounts.length === 0 && !showAddAccount && (
              <p className="text-theme-sm text-gray-400">
                No extra Pages connected yet — posts will use the default account from .env.
              </p>
            )}
            {facebookAccounts.length > 0 && (
              <div className="mb-3 space-y-2">
                {facebookAccounts.map((account: FacebookAccount) => (
                  <div
                    key={account.id}
                    className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2 dark:border-gray-800"
                  >
                    <div>
                      <p className="text-theme-sm font-medium text-gray-900 dark:text-white">{account.label}</p>
                      <p className="text-theme-xs text-gray-400">Page ID: {account.page_id}</p>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => deleteAccountMutation.mutate(account.id)}
                      disabled={deleteAccountMutation.isPending}
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      Remove
                    </Button>
                  </div>
                ))}
              </div>
            )}
            {showAddAccount ? (
              <div className="grid gap-3 sm:grid-cols-3">
                <div>
                  <Label htmlFor="fb-account-label">Label</Label>
                  <Input
                    id="fb-account-label"
                    value={newAccountLabel}
                    onChange={(e) => setNewAccountLabel(e.target.value)}
                    placeholder="e.g. Just post"
                  />
                </div>
                <div>
                  <Label htmlFor="fb-account-page-id">Page ID</Label>
                  <Input id="fb-account-page-id" value={newAccountPageId} onChange={(e) => setNewAccountPageId(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="fb-account-token">Page Access Token</Label>
                  <Input
                    id="fb-account-token"
                    type="password"
                    value={newAccountToken}
                    onChange={(e) => setNewAccountToken(e.target.value)}
                  />
                </div>
                <div className="flex gap-2 sm:col-span-3">
                  <Button
                    size="sm"
                    onClick={() => createAccountMutation.mutate()}
                    disabled={
                      createAccountMutation.isPending ||
                      !newAccountLabel.trim() ||
                      !newAccountPageId.trim() ||
                      !newAccountToken.trim()
                    }
                  >
                    {createAccountMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                    Save account
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setShowAddAccount(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <Button size="sm" variant="outline" onClick={() => setShowAddAccount(true)}>
                + Add Facebook account
              </Button>
            )}
          </CardContent>
        </Card>
      )}

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
            {selectedPlatforms.includes("facebook") && facebookAccounts.length > 0 && (
              <div className="sm:col-span-2">
                <Label htmlFor="social-fb-account">Facebook Page</Label>
                <select
                  id="social-fb-account"
                  value={facebookAccountId}
                  onChange={(e) => setFacebookAccountId(e.target.value === "" ? "" : Number(e.target.value))}
                  className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
                >
                  <option value="">Default (.env)</option>
                  {facebookAccounts.map((account: FacebookAccount) => (
                    <option key={account.id} value={account.id}>
                      {account.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
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
                    {post.platform === "facebook" && (
                      <span className="text-theme-xs text-gray-400">
                        via {facebookAccounts.find((a: FacebookAccount) => a.id === post.facebook_account_id)?.label ?? "Default (.env)"}
                      </span>
                    )}
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
                  {editingPostId === post.id ? (
                    <div className="space-y-2">
                      <textarea
                        value={editedContent}
                        onChange={(e) => setEditedContent(e.target.value)}
                        rows={6}
                        className="w-full rounded-lg border border-gray-300 bg-transparent p-3 text-theme-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800"
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => updateMutation.mutate({ id: post.id, content: editedContent })}
                          disabled={updateMutation.isPending || !editedContent.trim()}
                        >
                          {updateMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                          Save
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setEditingPostId(null)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="whitespace-pre-line text-theme-sm text-gray-700 dark:text-gray-300">{post.content}</p>
                  )}
                  {post.platform === "instagram" && !post.image_url && (
                    <p className="mt-1 text-theme-xs text-warning-500">
                      No image URL — this post can't be published to Instagram until one is added.
                    </p>
                  )}
                  {post.error && <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">{post.error}</p>}
                  {post.status !== "posted" && editingPostId !== post.id && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {post.status === "draft" && (
                        <>
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
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setEditingPostId(post.id);
                          setEditedContent(post.content);
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        Edit
                      </Button>
                    </div>
                  )}
                  {post.status === "draft" && editingPostId !== post.id && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => imageMutation.mutate(post.id)}
                        disabled={imageMutation.isPending && imageMutation.variables === post.id}
                      >
                        {imageMutation.isPending && imageMutation.variables === post.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <ImageIcon className="h-3.5 w-3.5" />
                        )}
                        {post.image_url ? "Regenerate image" : "Generate image"}
                      </Button>
                      <input
                        ref={(el) => {
                          uploadInputRefs.current[post.id] = el;
                        }}
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) uploadImageMutation.mutate({ id: post.id, file });
                          e.target.value = "";
                        }}
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => uploadInputRefs.current[post.id]?.click()}
                        disabled={uploadImageMutation.isPending && uploadImageMutation.variables?.id === post.id}
                      >
                        {uploadImageMutation.isPending && uploadImageMutation.variables?.id === post.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <ImageIcon className="h-3.5 w-3.5" />
                        )}
                        {post.image_url ? "Replace image" : "Upload image"}
                      </Button>
                    </div>
                  )}
                  {(post.status === "approved" || post.status === "failed") && editingPostId !== post.id && (
                    <Button
                      size="sm"
                      className="mt-3"
                      onClick={() => publishMutation.mutate(post.id)}
                      disabled={publishMutation.isPending && publishMutation.variables === post.id}
                    >
                      {publishMutation.isPending && publishMutation.variables === post.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Send className="h-3.5 w-3.5" />
                      )}
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

// Image generation, OG tags, interlink suggestions, and FAQ generation
// all had a working backend but no frontend UI at all — this panel is
// the fix, attached inline to each blog post card rather than a
// separate tab, since every one of these acts on one specific post.
function BlogSeoToolsPanel({ siteId, post }: { siteId: number; post: BlogPost }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [imagePrompt, setImagePrompt] = useState("");
  const [ogTags, setOgTags] = useState<OgTags | null>(null);
  const [related, setRelated] = useState<RelatedPage[] | null>(null);
  const [faqs, setFaqs] = useState<FaqPair[] | null>(null);

  const imageMutation = useMutation({
    mutationFn: () => generateBlogPostImage(post.id, imagePrompt.trim() || undefined),
    onSuccess: () => {
      toast.success("Image generated and uploaded to the site.");
      queryClient.invalidateQueries({ queryKey: ["seo", "blog", siteId] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Image generation failed.")),
  });

  const uploadImageMutation = useMutation({
    mutationFn: (file: File) => uploadBlogPostImage(post.id, file),
    onSuccess: () => {
      toast.success("Image uploaded to the site.");
      queryClient.invalidateQueries({ queryKey: ["seo", "blog", siteId] });
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Image upload failed.")),
  });
  const uploadInputRef = useRef<HTMLInputElement>(null);

  const ogMutation = useMutation({
    mutationFn: () =>
      generateOgTags({
        site_id: siteId,
        page_url: post.cms_post_link || `draft:${post.id}`,
        page_title: post.title,
        content_excerpt: post.excerpt || post.content.slice(0, 500),
      }),
    onSuccess: (data) => {
      setOgTags(data);
      toast.success("OG tags generated.");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "OG tag generation failed.")),
  });

  const interlinkMutation = useMutation({
    mutationFn: () =>
      suggestInterlinks({ site_id: siteId, url: post.cms_post_link || `draft:${post.id}`, title: post.title, content: post.content }),
    onSuccess: (data) => {
      setRelated(data);
      if (data.length === 0) toast.info("No related pages found yet — publish more posts first so there's something to link to.");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Interlink suggestion failed.")),
  });

  const faqMutation = useMutation({
    mutationFn: () => generateFaq({ site_id: siteId, page_title: post.title }),
    onSuccess: (data) => {
      setFaqs(data);
      toast.success("FAQ generated.");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "FAQ generation failed.")),
  });

  // Publishing already does this automatically — this is for a post
  // that was edited directly in the CMS afterward, so future posts'
  // interlink suggestions pick up the change.
  const reindexMutation = useMutation({
    mutationFn: () =>
      indexPageForInterlinks({ site_id: siteId, url: post.cms_post_link || `draft:${post.id}`, title: post.title, content: post.content }),
    onSuccess: () => toast.success("Indexed for interlinking — future posts can now link to this one."),
    onError: (err) => toast.error(serverErrorDetail(err, "Indexing failed.")),
  });

  return (
    <div className="mt-3 space-y-3 rounded-md border border-gray-100 bg-gray-50 p-3 dark:border-gray-800 dark:bg-white/5">
      <div>
        <p className="mb-1.5 text-theme-xs font-medium text-gray-500 dark:text-gray-400">Featured image</p>
        {post.image_url && (
          <a href={post.image_url} target="_blank" rel="noreferrer" className="mb-1.5 block truncate text-theme-xs text-brand-600 underline dark:text-brand-400">
            {post.image_url}
          </a>
        )}
        <div className="flex flex-wrap gap-2">
          <Input
            value={imagePrompt}
            onChange={(e) => setImagePrompt(e.target.value)}
            placeholder="Image prompt (optional — defaults to the post title)"
            className="max-w-xs"
          />
          <Button size="sm" variant="outline" onClick={() => imageMutation.mutate()} disabled={imageMutation.isPending}>
            {imageMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ImageIcon className="h-3.5 w-3.5" />}
            {post.image_url ? "Regenerate image" : "Generate image"}
          </Button>
          <input
            ref={uploadInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) uploadImageMutation.mutate(file);
              e.target.value = "";
            }}
          />
          <Button size="sm" variant="outline" onClick={() => uploadInputRef.current?.click()} disabled={uploadImageMutation.isPending}>
            {uploadImageMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ImageIcon className="h-3.5 w-3.5" />}
            Upload image
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={() => ogMutation.mutate()} disabled={ogMutation.isPending}>
          {ogMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          Generate OG tags
        </Button>
        <Button size="sm" variant="outline" onClick={() => interlinkMutation.mutate()} disabled={interlinkMutation.isPending}>
          {interlinkMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          Suggest interlinks
        </Button>
        <Button size="sm" variant="outline" onClick={() => faqMutation.mutate()} disabled={faqMutation.isPending}>
          {faqMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          Generate FAQ
        </Button>
        <Button size="sm" variant="outline" onClick={() => reindexMutation.mutate()} disabled={reindexMutation.isPending}>
          {reindexMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          Index for interlinking
        </Button>
      </div>

      {ogTags && (
        <div className="rounded-md border border-gray-200 bg-white p-2 text-theme-xs dark:border-gray-800 dark:bg-gray-900">
          <p><span className="text-gray-400">og:title — </span>{ogTags.og_title}</p>
          <p className="mt-1"><span className="text-gray-400">og:description — </span>{ogTags.og_description}</p>
        </div>
      )}

      {related && related.length > 0 && (
        <ul className="rounded-md border border-gray-200 bg-white p-2 text-theme-xs dark:border-gray-800 dark:bg-gray-900">
          {related.map((p) => (
            <li key={p.url} className="truncate">
              <a href={p.url} target="_blank" rel="noreferrer" className="text-brand-600 underline dark:text-brand-400">
                {p.title}
              </a>
            </li>
          ))}
        </ul>
      )}

      {faqs && faqs.length > 0 && (
        <div className="space-y-2 rounded-md border border-gray-200 bg-white p-2 text-theme-xs dark:border-gray-800 dark:bg-gray-900">
          {faqs.map((f, idx) => (
            <div key={idx}>
              <p className="font-medium text-gray-700 dark:text-gray-300">{f.question}</p>
              <p className="text-gray-500 dark:text-gray-400">{f.answer}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// The blueprint's "Content Word Limit + Structure" feature had a real
// backend (ai/seo/content_structure.py, /api/seo/content/analyze) but
// no way to use it on anything except a post this app itself generated
// — this is a general-purpose tool for any content, e.g. something
// written directly in the CMS.
function ContentStructureChecker() {
  const toast = useToast();
  const [content, setContent] = useState("");
  const [keyword, setKeyword] = useState("");
  const [report, setReport] = useState<StructureReport | null>(null);

  const analyzeMutation = useMutation({
    mutationFn: () => analyzeContentStructure({ content_html: content, primary_keyword: keyword.trim() || undefined }),
    onSuccess: (data) => setReport(data),
    onError: (err) => toast.error(serverErrorDetail(err, "Analysis failed.")),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <CaseSensitive className="h-4 w-4 text-brand-500" />
          Content structure checker
        </h2>
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          Paste any HTML content (e.g. something written directly in the CMS) to check word count, heading
          structure, and keyword usage against the same rules generated posts are held to.
        </p>
        <div className="space-y-3">
          <div>
            <Label htmlFor="structure-keyword">Primary keyword (optional)</Label>
            <Input id="structure-keyword" value={keyword} onChange={(e) => setKeyword(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="structure-content">Content (HTML)</Label>
            <RichTextEditor value={content} onChange={setContent} headings placeholder="Paste content here…" />
          </div>
          <Button onClick={() => analyzeMutation.mutate()} disabled={analyzeMutation.isPending || !content.trim()}>
            {analyzeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Analyze
          </Button>
        </div>
        {report && (
          <div className="mt-4 rounded-md border border-gray-100 bg-gray-50 p-4 dark:border-gray-800 dark:bg-white/5">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant={report.passed ? "success" : "warning"}>{report.passed ? "Passed" : `${report.issues.length} issue(s)`}</Badge>
              <span className="text-theme-xs text-gray-500 dark:text-gray-400">
                {report.word_count} words · H1×{report.h1_count} · H2×{report.h2_count} · H3×{report.h3_count}
              </span>
            </div>
            {report.issues.length > 0 && (
              <ul className="space-y-0.5">
                {report.issues.map((issue, idx) => (
                  <li key={idx} className="text-theme-xs text-gray-500 dark:text-gray-400">
                    <Badge variant={issue.severity === "error" ? "destructive" : "warning"} className="mr-1.5">
                      {issue.severity}
                    </Badge>
                    {issue.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function BlogTab({ siteId }: { siteId: number }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [topic, setTopic] = useState("");
  const [primaryKeyword, setPrimaryKeyword] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [seoToolsId, setSeoToolsId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editExcerpt, setEditExcerpt] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editSlug, setEditSlug] = useState("");
  const [editTags, setEditTags] = useState("");
  const [editCategories, setEditCategories] = useState("");

  const postsQuery = useQuery({ queryKey: ["seo", "blog", siteId], queryFn: () => getBlogPosts(siteId) });
  const posts = postsQuery.data ?? [];

  const startEditing = (post: BlogPost) => {
    setEditingId(post.id);
    setEditTitle(post.title);
    setEditExcerpt(post.excerpt ?? "");
    setEditContent(post.content);
    setEditSlug(post.slug ?? "");
    setEditTags(post.tags ? (JSON.parse(post.tags) as string[]).join(", ") : "");
    setEditCategories(post.categories ? (JSON.parse(post.categories) as string[]).join(", ") : "");
    setExpandedId(post.id);
  };

  const splitCsv = (value: string) =>
    value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

  const updateMutation = useMutation({
    mutationFn: async (postId: number) => {
      await updateBlogPost(postId, { title: editTitle, excerpt: editExcerpt, content: editContent });
      await updateBlogPostTaxonomy(postId, {
        slug: editSlug.trim() || undefined,
        tags: splitCsv(editTags),
        categories: splitCsv(editCategories),
      });
    },
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
        toast.success('Created as a draft in your CMS — click "Go Live" when you\'re ready to publish it for real.');
      } else {
        toast.error(result.error || "Publishing to the CMS failed.");
      }
      queryClient.invalidateQueries({ queryKey: ["seo", "blog", siteId] });
    },
  });

  const goLiveMutation = useMutation({
    mutationFn: (id: number) => goLiveBlogPost(id),
    onSuccess: (result) => {
      if (result.status === "live") {
        toast.success("It's live on the website.");
      } else {
        toast.error(result.error || "Couldn't make it live — see the error on the card.");
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
                          {post.status === "live" ? "View live post" : "View draft in CMS"}
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
                    {(post.slug || post.tags || post.categories) && (
                      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-theme-xs text-gray-400">
                        {post.slug && <span>/{post.slug}</span>}
                        {post.tags &&
                          (JSON.parse(post.tags) as string[]).map((tag) => (
                            <Badge key={tag} variant="outline">
                              {tag}
                            </Badge>
                          ))}
                        {post.categories &&
                          (JSON.parse(post.categories) as string[]).map((cat) => (
                            <Badge key={cat} variant="warning">
                              {cat}
                            </Badge>
                          ))}
                      </div>
                    )}
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <Button size="sm" variant="outline" onClick={() => setExpandedId(expandedId === post.id ? null : post.id)}>
                        {expandedId === post.id ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        {expandedId === post.id ? "Hide content" : "View content"}
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setSeoToolsId(seoToolsId === post.id ? null : post.id)}>
                        <Sparkles className="h-3.5 w-3.5" />
                        SEO Tools
                      </Button>
                      {(post.status === "draft" || post.status === "approved" || post.status === "failed") && (
                        <Button size="sm" variant="outline" onClick={() => startEditing(post)}>
                          <Pencil className="h-3.5 w-3.5" />
                          Edit
                        </Button>
                      )}
                      {post.status === "draft" && (
                        <>
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
                      {post.status === "published" && (
                        <Button size="sm" onClick={() => goLiveMutation.mutate(post.id)} disabled={goLiveMutation.isPending}>
                          {goLiveMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Globe className="h-3.5 w-3.5" />}
                          {post.error ? "Retry Go Live" : "Go Live"}
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
                        <div className="grid gap-3 sm:grid-cols-3">
                          <div>
                            <Label htmlFor={`blog-edit-slug-${post.id}`}>Slug</Label>
                            <Input
                              id={`blog-edit-slug-${post.id}`}
                              value={editSlug}
                              onChange={(e) => setEditSlug(e.target.value)}
                              placeholder="url-friendly-slug"
                            />
                          </div>
                          <div>
                            <Label htmlFor={`blog-edit-tags-${post.id}`}>Tags</Label>
                            <Input
                              id={`blog-edit-tags-${post.id}`}
                              value={editTags}
                              onChange={(e) => setEditTags(e.target.value)}
                              placeholder="comma, separated, tags"
                            />
                          </div>
                          <div>
                            <Label htmlFor={`blog-edit-categories-${post.id}`}>Categories</Label>
                            <Input
                              id={`blog-edit-categories-${post.id}`}
                              value={editCategories}
                              onChange={(e) => setEditCategories(e.target.value)}
                              placeholder="comma, separated"
                            />
                          </div>
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
                    {seoToolsId === post.id && <BlogSeoToolsPanel siteId={siteId} post={post} />}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <ContentStructureChecker />
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

// Truncates the middle of a long asset URL so a real minified filename
// (often 80+ characters with a cache-busting query string) doesn't blow
// out the row width — keeps the meaningful start and end, not just a
// trailing cut that hides the filename.
function shortenResourceUrl(url: string, max = 70): string {
  if (url.length <= max) return url;
  const head = Math.ceil((max - 1) * 0.6);
  const tail = max - 1 - head;
  return `${url.slice(0, head)}…${url.slice(url.length - tail)}`;
}

function OpportunitiesPanel({
  resultId,
  siteId,
  onEditStaticFile,
}: {
  resultId: number;
  siteId: number;
  onEditStaticFile: (path: string) => void;
}) {
  const toast = useToast();
  const oppQuery = useQuery({
    queryKey: ["seo", "pagespeed-opportunities", resultId],
    queryFn: () => getPageSpeedOpportunities(resultId),
  });

  const editTargetMutation = useMutation({
    mutationFn: (url: string) => getUrlEditTarget(siteId, url),
    onSuccess: (target) => {
      if (target.kind === "cms" && target.edit_url) {
        window.open(target.edit_url, "_blank", "noopener,noreferrer");
      } else if (target.kind === "static_file" && target.file_path) {
        onEditStaticFile(target.file_path);
      } else {
        toast.error(target.detail);
      }
    },
    onError: (err) => {
      const detail = (err as AxiosError<{ detail?: string }>).response?.data?.detail;
      toast.error(detail || "Could not resolve where to edit this resource.");
    },
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
              {o.items.length > 0 && (
                <div className="mt-2 space-y-1.5 border-t border-gray-100 pt-2 dark:border-gray-800">
                  <p className="text-theme-xs font-medium text-gray-500 dark:text-gray-400">
                    Affected {o.items.length === 1 ? "file" : "files"} — exactly where this shows up:
                  </p>
                  {o.items.map((item, idx) => (
                    <div
                      key={`${item.url}-${idx}`}
                      className="flex flex-wrap items-center justify-between gap-2 rounded bg-gray-50 px-2 py-1.5 dark:bg-white/5"
                    >
                      <div className="min-w-0">
                        <p className="break-all text-theme-xs text-gray-700 dark:text-gray-300" title={item.url ?? ""}>
                          {item.url ? shortenResourceUrl(item.url) : "—"}
                        </p>
                        <p className="text-theme-xs text-gray-400">
                          {item.wasted_bytes ? `~${formatKb(item.wasted_bytes / 1024)} wasted` : ""}
                          {item.wasted_bytes && item.wasted_ms ? " · " : ""}
                          {item.wasted_ms ? `~${formatMs(item.wasted_ms)} wasted` : ""}
                        </p>
                      </div>
                      {item.url && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => editTargetMutation.mutate(item.url as string)}
                          disabled={editTargetMutation.isPending}
                        >
                          {editTargetMutation.isPending ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <ExternalLink className="h-3.5 w-3.5" />
                          )}
                          Edit
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PerformanceTab({
  siteId,
  siteUrl,
  onEditStaticFile,
}: {
  siteId: number;
  siteUrl: string;
  onEditStaticFile: (path: string) => void;
}) {
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
                  {expandedId === r.id && (
                    <OpportunitiesPanel resultId={r.id} siteId={siteId} onEditStaticFile={onEditStaticFile} />
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

// GSC's own "country" dimension returns lowercase ISO 3166-1 alpha-3
// codes (Google's documented convention for this field — e.g. "usa",
// not "US") — the real Search Console UI shows the country's name, not
// this code, so this table translates it the same way for parity. A
// code not in this table (rare/unrecognized) falls back to its own
// uppercased form rather than guessing a name.
const ISO_ALPHA3_COUNTRY_NAMES: Record<string, string> = {
  afg: "Afghanistan", alb: "Albania", dza: "Algeria", and: "Andorra", ago: "Angola",
  arg: "Argentina", arm: "Armenia", aus: "Australia", aut: "Austria", aze: "Azerbaijan",
  bhs: "Bahamas", bhr: "Bahrain", bgd: "Bangladesh", brb: "Barbados", blr: "Belarus",
  bel: "Belgium", blz: "Belize", ben: "Benin", btn: "Bhutan", bol: "Bolivia",
  bih: "Bosnia and Herzegovina", bwa: "Botswana", bra: "Brazil", brn: "Brunei", bgr: "Bulgaria",
  bfa: "Burkina Faso", bdi: "Burundi", khm: "Cambodia", cmr: "Cameroon", can: "Canada",
  cpv: "Cabo Verde", caf: "Central African Republic", tcd: "Chad", chl: "Chile", chn: "China",
  col: "Colombia", com: "Comoros", cog: "Congo", cod: "DR Congo", cri: "Costa Rica",
  civ: "Côte d'Ivoire", hrv: "Croatia", cub: "Cuba", cyp: "Cyprus", cze: "Czechia",
  dnk: "Denmark", dji: "Djibouti", dma: "Dominica", dom: "Dominican Republic", ecu: "Ecuador",
  egy: "Egypt", slv: "El Salvador", gnq: "Equatorial Guinea", eri: "Eritrea", est: "Estonia",
  swz: "Eswatini", eth: "Ethiopia", fji: "Fiji", fin: "Finland", fra: "France",
  gab: "Gabon", gmb: "Gambia", geo: "Georgia", deu: "Germany", gha: "Ghana",
  grc: "Greece", grd: "Grenada", gtm: "Guatemala", gin: "Guinea", gnb: "Guinea-Bissau",
  guy: "Guyana", hti: "Haiti", hnd: "Honduras", hkg: "Hong Kong", hun: "Hungary",
  isl: "Iceland", ind: "India", idn: "Indonesia", irn: "Iran", irq: "Iraq",
  irl: "Ireland", isr: "Israel", ita: "Italy", jam: "Jamaica", jpn: "Japan",
  jor: "Jordan", kaz: "Kazakhstan", ken: "Kenya", kir: "Kiribati", kwt: "Kuwait",
  kgz: "Kyrgyzstan", lao: "Laos", lva: "Latvia", lbn: "Lebanon", lso: "Lesotho",
  lbr: "Liberia", lby: "Libya", lie: "Liechtenstein", ltu: "Lithuania", lux: "Luxembourg",
  mac: "Macao", mdg: "Madagascar", mwi: "Malawi", mys: "Malaysia", mdv: "Maldives",
  mli: "Mali", mlt: "Malta", mrt: "Mauritania", mus: "Mauritius", mex: "Mexico",
  mda: "Moldova", mco: "Monaco", mng: "Mongolia", mne: "Montenegro", mar: "Morocco",
  moz: "Mozambique", mmr: "Myanmar", nam: "Namibia", npl: "Nepal", nld: "Netherlands",
  nzl: "New Zealand", nic: "Nicaragua", ner: "Niger", nga: "Nigeria", prk: "North Korea",
  mkd: "North Macedonia", nor: "Norway", omn: "Oman", pak: "Pakistan", pan: "Panama",
  png: "Papua New Guinea", pry: "Paraguay", per: "Peru", phl: "Philippines", pol: "Poland",
  prt: "Portugal", pri: "Puerto Rico", qat: "Qatar", rou: "Romania", rus: "Russia",
  rwa: "Rwanda", sau: "Saudi Arabia", sen: "Senegal", srb: "Serbia", syc: "Seychelles",
  sle: "Sierra Leone", sgp: "Singapore", svk: "Slovakia", svn: "Slovenia", som: "Somalia",
  zaf: "South Africa", kor: "South Korea", ssd: "South Sudan", esp: "Spain", lka: "Sri Lanka",
  sdn: "Sudan", sur: "Suriname", swe: "Sweden", che: "Switzerland", syr: "Syria",
  twn: "Taiwan", tjk: "Tajikistan", tza: "Tanzania", tha: "Thailand", tls: "Timor-Leste",
  tgo: "Togo", ton: "Tonga", tto: "Trinidad and Tobago", tun: "Tunisia", tur: "Turkey",
  tkm: "Turkmenistan", uga: "Uganda", ukr: "Ukraine", are: "United Arab Emirates",
  gbr: "United Kingdom", usa: "United States", ury: "Uruguay", uzb: "Uzbekistan",
  vut: "Vanuatu", vat: "Vatican City", ven: "Venezuela", vnm: "Vietnam", yem: "Yemen",
  zmb: "Zambia", zwe: "Zimbabwe",
};

// Matches the real Search Console UI's own presentation of each
// dimension's values, not the raw API enum this app's backend passes
// through as-is (ISO codes for country, SCREAMING_CASE for device/
// search appearance).
function formatGscDimensionKey(dimension: string, key: string): string {
  if (dimension === "country") return ISO_ALPHA3_COUNTRY_NAMES[key.toLowerCase()] ?? key.toUpperCase();
  if (dimension === "device") return key.charAt(0).toUpperCase() + key.slice(1).toLowerCase();
  // search-appearance: no official Google label list to draw from here —
  // title-casing the enum's own words ("AMP_BLUE_LINK" -> "Amp Blue
  // Link") is a readable, honest fallback rather than inventing exact
  // Search Console wording this app hasn't verified.
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

type GscTabKey = "queries" | "pages" | "countries" | "devices" | "search-appearance";

const GSC_TABS: { key: GscTabKey; label: string }[] = [
  { key: "queries", label: "Queries" },
  { key: "pages", label: "Pages" },
  { key: "countries", label: "Countries" },
  { key: "devices", label: "Devices" },
  { key: "search-appearance", label: "Search Appearance" },
];

// Matches the real Search Console UI's own date-range chips. "24 hours"
// is included for parity even though the public API's data has a real
// ~2-3 day processing lag — a same-day range will often come back
// genuinely empty, which is an honest result, not a bug, so it's left
// in rather than second-guessed away.
const GSC_DATE_RANGES = [
  { key: "24h", label: "24 hours", days: 1 },
  { key: "7d", label: "7 days", days: 7 },
  { key: "28d", label: "28 days", days: 28 },
  { key: "3m", label: "3 months", days: 90 },
  { key: "custom", label: "Custom", days: null },
] as const;

interface GscPerfRow {
  label: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
  rawKey?: string;
}

// GA4's own dimension values are already human-readable (full country
// names, "google"/"(direct)" for source) unlike GSC's coded values —
// the only one worth reformatting here is deviceCategory's lowercase
// "desktop"/"mobile"/"tablet".
function formatGa4DimensionKey(key: string): string {
  return key.charAt(0).toUpperCase() + key.slice(1).toLowerCase();
}

type Ga4TabKey = "pages" | "sources" | "countries" | "devices";

const GA4_TABS: { key: Ga4TabKey; label: string }[] = [
  { key: "pages", label: "Pages" },
  { key: "sources", label: "Sources" },
  { key: "countries", label: "Countries" },
  { key: "devices", label: "Devices" },
];

const GA4_DATE_RANGES = [
  { key: "24h", label: "24 hours", days: 1 },
  { key: "7d", label: "7 days", days: 7 },
  { key: "28d", label: "28 days", days: 28 },
  { key: "3m", label: "3 months", days: 90 },
  { key: "custom", label: "Custom", days: null },
] as const;

// Module 54 — the switchable metric on GA4's own Home report card
// ("Active users ▾ 266  ↑0.8%"), with a searchable/categorized picker
// matching GA4's own "Search items" dropdown. Grouped into the same
// User/Session/Event categories GA4 itself uses, but only with the 9
// metrics ga4_client.py's _METRICS actually fetches per day — GA4's
// fuller picker also has Ecommerce/Revenue/Page-screen categories this
// app has no data for, so those are left out rather than shown empty
// or faked.
type Ga4HeadlineMetricKey =
  | "active_users"
  | "new_users"
  | "total_users"
  | "sessions"
  | "engaged_sessions"
  | "engagement_rate"
  | "avg_session_duration"
  | "event_count"
  | "conversions";

const GA4_HEADLINE_METRICS: { key: Ga4HeadlineMetricKey; label: string; category: "User" | "Session" | "Event" }[] = [
  { key: "active_users", label: "Active users", category: "User" },
  { key: "new_users", label: "New users", category: "User" },
  { key: "total_users", label: "Total users", category: "User" },
  { key: "sessions", label: "Sessions", category: "Session" },
  { key: "engaged_sessions", label: "Engaged sessions", category: "Session" },
  { key: "engagement_rate", label: "Engagement rate", category: "Session" },
  { key: "avg_session_duration", label: "Average session duration", category: "Session" },
  { key: "event_count", label: "Event count", category: "Event" },
  { key: "conversions", label: "Conversions", category: "Event" },
];

// engagement_rate/avg_session_duration are rates, not counts — summing
// them across days the way sessions/active users are summed would be
// meaningless (a 7-day engagement rate could add up to "210%"), so
// these two are session-weighted-averaged instead, the same technique
// this panel's own avgBounceRate stat already uses.
const GA4_RATE_METRICS: Ga4HeadlineMetricKey[] = ["engagement_rate", "avg_session_duration"];

function computeHeadlineMetricValue(rows: Ga4DateRow[], key: Ga4HeadlineMetricKey): number {
  if (GA4_RATE_METRICS.includes(key)) {
    const totalSessions = rows.reduce((sum, r) => sum + r.sessions, 0);
    if (totalSessions === 0) return 0;
    return rows.reduce((sum, r) => sum + r[key] * r.sessions, 0) / totalSessions;
  }
  return rows.reduce((sum, r) => sum + r[key], 0);
}

function formatHeadlineMetricValue(key: Ga4HeadlineMetricKey, value: number): string {
  if (key === "engagement_rate") return `${(value * 100).toFixed(1)}%`;
  if (key === "avg_session_duration") {
    const totalSeconds = Math.round(value);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
  }
  return Math.round(value).toLocaleString();
}

function shiftIsoDate(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

// The immediately preceding period of equal length — the same
// comparison GA4's own Home report trend arrow uses ("vs previous
// period"). Returns explicit start/end dates so it can reuse the exact
// same /ga4/timeseries endpoint the main chart already calls, just with
// an overridden range instead of days_back.
function getPreviousPeriodFilters(filters: Ga4FilterParams): Ga4FilterParams | null {
  if (filters.startDate && filters.endDate) {
    const dayCount =
      Math.round(
        (new Date(filters.endDate + "T00:00:00").getTime() - new Date(filters.startDate + "T00:00:00").getTime()) / 86_400_000
      ) + 1;
    const prevEnd = shiftIsoDate(filters.startDate, -1);
    return { startDate: shiftIsoDate(prevEnd, -(dayCount - 1)), endDate: prevEnd };
  }
  if (filters.daysBack) {
    const todayStr = new Date().toISOString().slice(0, 10);
    const currentStart = shiftIsoDate(todayStr, -(filters.daysBack - 1));
    const prevEnd = shiftIsoDate(currentStart, -1);
    return { startDate: shiftIsoDate(prevEnd, -(filters.daysBack - 1)), endDate: prevEnd };
  }
  return null;
}

interface Ga4PerfRow {
  label: string;
  sessions: number;
  bounceRate: number;
  conversions: number;
}

function formatDayLabel(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return Number.isNaN(d.getTime()) ? dateStr : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function GscTrendChart({ data }: { data: GscDateRow[] }) {
  const [showClicks, setShowClicks] = useState(true);
  const [showImpressions, setShowImpressions] = useState(true);
  const chartData = data.map((d) => ({ ...d, label: formatDayLabel(d.date) }));

  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-4 text-theme-xs">
        <label className="flex cursor-pointer items-center gap-1.5 text-gray-600 dark:text-gray-300">
          <input type="checkbox" checked={showClicks} onChange={(e) => setShowClicks(e.target.checked)} />
          <span className="inline-block h-2 w-2 rounded-full bg-brand-500" /> Clicks
        </label>
        <label className="flex cursor-pointer items-center gap-1.5 text-gray-600 dark:text-gray-300">
          <input type="checkbox" checked={showImpressions} onChange={(e) => setShowImpressions(e.target.checked)} />
          <span className="inline-block h-2 w-2 rounded-full bg-purple-500" /> Impressions
        </label>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-100 dark:stroke-gray-800" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={30} />
          <YAxis yAxisId="clicks" tick={{ fontSize: 11 }} width={40} />
          <YAxis yAxisId="impressions" orientation="right" tick={{ fontSize: 11 }} width={40} />
          <Tooltip
            formatter={(value, name) => [value, name === "clicks" ? "Clicks" : "Impressions"]}
            labelFormatter={(label) => label}
          />
          {showClicks && (
            <Line yAxisId="clicks" type="monotone" dataKey="clicks" stroke="#465fff" strokeWidth={2} dot={false} name="clicks" />
          )}
          {showImpressions && (
            <Line
              yAxisId="impressions"
              type="monotone"
              dataKey="impressions"
              stroke="#a855f7"
              strokeWidth={2}
              dot={false}
              name="impressions"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function GscPerformancePanel({ siteId }: { siteId: number }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<GscTabKey>("queries");
  const [rangeKey, setRangeKey] = useState<(typeof GSC_DATE_RANGES)[number]["key"]>("3m");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [countryFilter, setCountryFilter] = useState<string | null>(null);
  const [pageFilter, setPageFilter] = useState<string | null>(null);

  const activeRange = GSC_DATE_RANGES.find((r) => r.key === rangeKey)!;
  const customReady = rangeKey === "custom" && !!customStart && !!customEnd;
  const filters: GscFilterParams =
    rangeKey === "custom"
      ? { startDate: customStart || undefined, endDate: customEnd || undefined, country: countryFilter, page: pageFilter }
      : { daysBack: activeRange.days ?? 90, country: countryFilter, page: pageFilter };
  // Custom range isn't queryable until both dates are picked — every hook
  // below stays disabled rather than firing on a half-entered range.
  const rangeIsReady = rangeKey !== "custom" || customReady;

  const timeseriesQuery = useQuery({
    queryKey: ["seo", "gsc-timeseries", siteId, filters],
    queryFn: () => getGscTimeseries(siteId, filters),
    enabled: rangeIsReady,
  });
  const timeseries = timeseriesQuery.data ?? [];
  const totals = timeseries.reduce(
    (acc, d) => ({ clicks: acc.clicks + d.clicks, impressions: acc.impressions + d.impressions, posWeighted: acc.posWeighted + d.position * d.impressions }),
    { clicks: 0, impressions: 0, posWeighted: 0 }
  );
  const avgCtr = totals.impressions > 0 ? totals.clicks / totals.impressions : 0;
  const avgPosition = totals.impressions > 0 ? totals.posWeighted / totals.impressions : 0;

  const queriesQuery = useQuery({
    queryKey: ["seo", "gsc-live-queries", siteId, filters],
    queryFn: () => getGscQueriesLive(siteId, filters),
    enabled: tab === "queries" && rangeIsReady,
  });
  const pagesQuery = useQuery({
    queryKey: ["seo", "gsc-live-pages", siteId, filters],
    queryFn: () => getGscPagesLive(siteId, filters),
    enabled: tab === "pages" && rangeIsReady,
  });
  const countriesQuery = useQuery({
    queryKey: ["seo", "gsc-live-countries", siteId, filters.daysBack, filters.startDate, filters.endDate, filters.page],
    queryFn: () => getGscByCountry(siteId, { ...filters, country: undefined }),
    enabled: tab === "countries" && rangeIsReady,
  });
  const devicesQuery = useQuery({
    queryKey: ["seo", "gsc-live-devices", siteId, filters],
    queryFn: () => getGscByDevice(siteId, filters),
    enabled: tab === "devices" && rangeIsReady,
  });
  const appearanceQuery = useQuery({
    queryKey: ["seo", "gsc-live-appearance", siteId, filters],
    queryFn: () => getGscBySearchAppearance(siteId, filters),
    enabled: tab === "search-appearance" && rangeIsReady,
  });

  const activeQuery = {
    queries: queriesQuery,
    pages: pagesQuery,
    countries: countriesQuery,
    devices: devicesQuery,
    "search-appearance": appearanceQuery,
  }[tab];

  const rows: GscPerfRow[] =
    tab === "queries"
      ? (queriesQuery.data ?? []).map((r) => ({ label: r.query, clicks: r.clicks, impressions: r.impressions, ctr: r.ctr, position: r.position }))
      : tab === "pages"
        ? (pagesQuery.data ?? []).map((r) => ({ label: r.page, rawKey: r.page, clicks: r.clicks, impressions: r.impressions, ctr: r.ctr, position: r.position }))
        : tab === "countries"
          ? (countriesQuery.data ?? []).map((r) => ({
              label: formatGscDimensionKey("country", r.key),
              rawKey: r.key,
              clicks: r.clicks,
              impressions: r.impressions,
              ctr: r.ctr,
              position: r.position,
            }))
          : tab === "devices"
            ? (devicesQuery.data ?? []).map((r) => ({ label: formatGscDimensionKey("device", r.key), clicks: r.clicks, impressions: r.impressions, ctr: r.ctr, position: r.position }))
            : (appearanceQuery.data ?? []).map((r) => ({
                label: formatGscDimensionKey("search-appearance", r.key),
                clicks: r.clicks,
                impressions: r.impressions,
                ctr: r.ctr,
                position: r.position,
              }));

  const columnLabel = GSC_TABS.find((t) => t.key === tab)!.label.replace(/s$/, "");
  const rowIsClickable = tab === "countries" || tab === "pages";

  const handleRowClick = (row: GscPerfRow) => {
    if (!row.rawKey) return;
    if (tab === "countries") {
      setCountryFilter(row.rawKey);
      setTab("queries");
    } else if (tab === "pages") {
      setPageFilter(row.rawKey);
    }
  };

  const hasFilters = !!countryFilter || !!pageFilter;
  const resetFilters = () => {
    setCountryFilter(null);
    setPageFilter(null);
  };

  const dateRangeLabel =
    rangeKey === "custom" ? `Custom (${customStart || "?"} to ${customEnd || "?"})` : activeRange.label;

  const exportMutation = useMutation({
    // Fetches all 5 dimensions (not just whichever tab is on screen) so
    // one click writes Queries/Pages/Countries/Devices/Search Appearance
    // into their own clean tabs — reuses the same query keys the tabs'
    // own useQuery hooks use, so an already-loaded tab isn't re-fetched.
    mutationFn: async () => {
      const [queriesData, pagesData, countriesData, devicesData, appearanceData] = await Promise.all([
        queryClient.fetchQuery({ queryKey: ["seo", "gsc-live-queries", siteId, filters], queryFn: () => getGscQueriesLive(siteId, filters) }),
        queryClient.fetchQuery({ queryKey: ["seo", "gsc-live-pages", siteId, filters], queryFn: () => getGscPagesLive(siteId, filters) }),
        queryClient.fetchQuery({
          queryKey: ["seo", "gsc-live-countries", siteId, filters.daysBack, filters.startDate, filters.endDate, filters.page],
          queryFn: () => getGscByCountry(siteId, { ...filters, country: undefined }),
        }),
        queryClient.fetchQuery({ queryKey: ["seo", "gsc-live-devices", siteId, filters], queryFn: () => getGscByDevice(siteId, filters) }),
        queryClient.fetchQuery({ queryKey: ["seo", "gsc-live-appearance", siteId, filters], queryFn: () => getGscBySearchAppearance(siteId, filters) }),
      ]);
      return exportAllGscToSheet(siteId, dateRangeLabel, GSC_TABS.find((t) => t.key === tab)!.label, {
        queries: queriesData.map((r) => ({ label: r.query, clicks: r.clicks, impressions: r.impressions, ctr: r.ctr, position: r.position })),
        pages: pagesData.map((r) => ({ label: r.page, clicks: r.clicks, impressions: r.impressions, ctr: r.ctr, position: r.position })),
        countries: countriesData.map((r) => ({
          label: formatGscDimensionKey("country", r.key),
          clicks: r.clicks,
          impressions: r.impressions,
          ctr: r.ctr,
          position: r.position,
        })),
        devices: devicesData.map((r) => ({
          label: formatGscDimensionKey("device", r.key),
          clicks: r.clicks,
          impressions: r.impressions,
          ctr: r.ctr,
          position: r.position,
        })),
        search_appearance: appearanceData.map((r) => ({
          label: formatGscDimensionKey("search-appearance", r.key),
          clicks: r.clicks,
          impressions: r.impressions,
          ctr: r.ctr,
          position: r.position,
        })),
        timeseries,
      });
    },
    onSuccess: (result) => {
      if (!result.ok) {
        toast.error(result.detail);
        return;
      }
      toast.success(result.detail);
      // Opens straight to the tab matching whatever view is on screen —
      // the bare spreadsheet link opens whatever tab was last active,
      // which made a real, successful export look like it hadn't
      // written anything. The other 4 dimension tabs are populated too,
      // reachable via the tab strip at the bottom of the sheet.
      if (result.sheet_url) window.open(result.sheet_url, "_blank", "noopener,noreferrer");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Export to Sheets failed.")),
  });

  // Downloads ALL 5 dimensions in one file (one section per view —
  // Queries/Pages/Countries/Devices/Search Appearance), not just
  // whichever tab is on screen — mirrors exportMutation's "fetch every
  // dimension" approach so both buttons give the same complete data.
  const downloadCsvMutation = useMutation({
    mutationFn: async () => {
      const [queriesData, pagesData, countriesData, devicesData, appearanceData] = await Promise.all([
        queryClient.fetchQuery({ queryKey: ["seo", "gsc-live-queries", siteId, filters], queryFn: () => getGscQueriesLive(siteId, filters) }),
        queryClient.fetchQuery({ queryKey: ["seo", "gsc-live-pages", siteId, filters], queryFn: () => getGscPagesLive(siteId, filters) }),
        queryClient.fetchQuery({
          queryKey: ["seo", "gsc-live-countries", siteId, filters.daysBack, filters.startDate, filters.endDate, filters.page],
          queryFn: () => getGscByCountry(siteId, { ...filters, country: undefined }),
        }),
        queryClient.fetchQuery({ queryKey: ["seo", "gsc-live-devices", siteId, filters], queryFn: () => getGscByDevice(siteId, filters) }),
        queryClient.fetchQuery({ queryKey: ["seo", "gsc-live-appearance", siteId, filters], queryFn: () => getGscBySearchAppearance(siteId, filters) }),
      ]);

      const toRow = (label: string, r: { clicks: number; impressions: number; ctr: number; position: number }) => [
        label,
        String(r.clicks),
        String(r.impressions),
        `${(r.ctr * 100).toFixed(2)}%`,
        r.position.toFixed(1),
      ];
      const sections: { title: string; column: string; rows: string[][] }[] = [
        { title: "Queries", column: "Query", rows: queriesData.map((r) => toRow(r.query, r)) },
        { title: "Pages", column: "Page", rows: pagesData.map((r) => toRow(r.page, r)) },
        { title: "Countries", column: "Country", rows: countriesData.map((r) => toRow(formatGscDimensionKey("country", r.key), r)) },
        { title: "Devices", column: "Device", rows: devicesData.map((r) => toRow(formatGscDimensionKey("device", r.key), r)) },
        { title: "Search Appearance", column: "Search Appearance", rows: appearanceData.map((r) => toRow(formatGscDimensionKey("search-appearance", r.key), r)) },
      ];

      const escape = (cell: string) => `"${cell.replace(/"/g, '""')}"`;
      const csv = sections
        .map((s) =>
          [
            escape(s.title),
            [s.column, "Clicks", "Impressions", "CTR", "Avg. Position"].map(escape).join(","),
            ...(s.rows.length ? s.rows.map((row) => row.map(escape).join(",")) : [escape("(no rows)")]),
          ].join("\r\n")
        )
        .join("\r\n\r\n");

      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gsc-all-${dateRangeLabel.replace(/[^a-z0-9]+/gi, "-")}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Download failed.")),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <BarChart3 className="h-4 w-4 text-brand-500" />
            Search Console Performance
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-white/5">
              {GSC_DATE_RANGES.map((r) => (
                <button
                  key={r.key}
                  onClick={() => setRangeKey(r.key)}
                  className={`rounded-md px-3 py-1 text-theme-xs font-medium transition-colors ${
                    rangeKey === r.key ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white" : "text-gray-500"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
            {hasFilters && (
              <Button size="sm" variant="outline" onClick={resetFilters}>
                Reset filters
              </Button>
            )}
          </div>
        </div>

        {rangeKey === "custom" && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Label htmlFor="gsc-custom-start" className="mb-0">
              From
            </Label>
            <Input id="gsc-custom-start" type="date" value={customStart} onChange={(e) => setCustomStart(e.target.value)} className="max-w-40" />
            <Label htmlFor="gsc-custom-end" className="mb-0">
              To
            </Label>
            <Input id="gsc-custom-end" type="date" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} className="max-w-40" />
            {!customReady && <span className="text-theme-xs text-gray-400">Pick both dates to load data.</span>}
          </div>
        )}

        {(countryFilter || pageFilter) && (
          <div className="mb-3 flex flex-wrap gap-2">
            {pageFilter && (
              <Badge variant="outline">
                Page: {pageFilter}
                <button onClick={() => setPageFilter(null)} className="ml-1.5 align-middle">
                  <XCircle className="h-3 w-3" />
                </button>
              </Badge>
            )}
            {countryFilter && (
              <Badge variant="outline">
                Country: {formatGscDimensionKey("country", countryFilter)}
                <button onClick={() => setCountryFilter(null)} className="ml-1.5 align-middle">
                  <XCircle className="h-3 w-3" />
                </button>
              </Badge>
            )}
          </div>
        )}

        {rangeIsReady && (
          <>
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg border border-brand-200 bg-brand-50 p-3 dark:border-brand-500/30 dark:bg-brand-500/10">
                <p className="text-theme-xs text-brand-700 dark:text-brand-300">Total clicks</p>
                <p className="text-xl font-semibold text-brand-800 dark:text-brand-200">{totals.clicks.toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-purple-200 bg-purple-50 p-3 dark:border-purple-500/30 dark:bg-purple-500/10">
                <p className="text-theme-xs text-purple-700 dark:text-purple-300">Total impressions</p>
                <p className="text-xl font-semibold text-purple-800 dark:text-purple-200">{totals.impressions.toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-theme-xs text-gray-400">Average CTR</p>
                <p className="text-xl font-semibold text-gray-900 dark:text-white">{(avgCtr * 100).toFixed(1)}%</p>
              </div>
              <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-theme-xs text-gray-400">Average position</p>
                <p className="text-xl font-semibold text-gray-900 dark:text-white">{avgPosition.toFixed(1)}</p>
              </div>
            </div>

            {timeseriesQuery.isLoading ? (
              <div className="mb-4 flex h-24 items-center justify-center text-gray-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : timeseriesQuery.isError ? (
              <p className="mb-4 text-theme-sm text-error-500">{serverErrorDetail(timeseriesQuery.error, "GSC fetch failed.")}</p>
            ) : timeseries.length === 0 ? (
              <p className="mb-4 text-theme-sm text-gray-400">No data for this date range.</p>
            ) : (
              <div className="mb-4">
                <GscTrendChart data={timeseries} />
              </div>
            )}
          </>
        )}

        <div className="mb-3 flex flex-wrap gap-4 border-b border-gray-100 dark:border-gray-800">
          {GSC_TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`-mb-px border-b-2 pb-2 text-theme-xs font-semibold tracking-wide uppercase transition-colors ${
                tab === t.key
                  ? "border-brand-500 text-gray-900 dark:text-white"
                  : "border-transparent text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {!rangeIsReady ? null : activeQuery.isLoading ? (
          <div className="flex h-16 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : activeQuery.isError ? (
          <p className="text-theme-sm text-error-500">{serverErrorDetail(activeQuery.error, "GSC fetch failed.")}</p>
        ) : rows.length === 0 ? (
          <p className="text-theme-sm text-gray-400">No rows for this view in the selected date range.</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="mb-2 flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => downloadCsvMutation.mutate()} disabled={downloadCsvMutation.isPending}>
                {downloadCsvMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                Download CSV
              </Button>
              <Button size="sm" variant="outline" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
                {exportMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                Export All to Sheets
              </Button>
            </div>
            <table className="w-full text-left text-theme-sm">
              <thead>
                <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                  <th className="py-2 pr-3 font-medium">{columnLabel}</th>
                  <th className="py-2 pr-3 font-medium">Clicks</th>
                  <th className="py-2 pr-3 font-medium">Impressions</th>
                  <th className="py-2 pr-3 font-medium">CTR</th>
                  <th className="py-2 font-medium">Avg. position</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr
                    key={i}
                    onClick={() => handleRowClick(r)}
                    className={`border-b border-gray-50 dark:border-gray-800/50 ${
                      rowIsClickable ? "cursor-pointer hover:bg-gray-50 dark:hover:bg-white/5" : ""
                    }`}
                  >
                    <td
                      className={`max-w-xs truncate py-2 pr-3 ${
                        rowIsClickable ? "text-brand-600 hover:underline dark:text-brand-400" : "text-gray-700 dark:text-gray-300"
                      }`}
                    >
                      {r.label}
                    </td>
                    <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{r.clicks}</td>
                    <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{r.impressions}</td>
                    <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{(r.ctr * 100).toFixed(1)}%</td>
                    <td className="py-2 text-gray-500 dark:text-gray-400">{r.position.toFixed(1)}</td>
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

// Plots whichever two metrics the headline cards above have selected —
// previously hardcoded to Sessions/Conversions, which meant switching a
// card's dropdown updated its own number but left the chart showing
// unrelated data. metricA/metricB (and their matching colors) come
// straight from Ga4PerformancePanel's own headlineMetricA/B state, so
// the chart and the two cards always agree on what's on screen.
function Ga4TrendChart({ data, metricA, metricB }: { data: Ga4DateRow[]; metricA: Ga4HeadlineMetricKey; metricB: Ga4HeadlineMetricKey }) {
  const [showA, setShowA] = useState(true);
  const [showB, setShowB] = useState(true);
  const chartData = data.map((d) => ({ ...d, label: formatDayLabel(d.date) }));
  const labelA = GA4_HEADLINE_METRICS.find((m) => m.key === metricA)!.label;
  const labelB = GA4_HEADLINE_METRICS.find((m) => m.key === metricB)!.label;
  const sameMetric = metricA === metricB;

  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-4 text-theme-xs">
        <label className="flex cursor-pointer items-center gap-1.5 text-gray-600 dark:text-gray-300">
          <input type="checkbox" checked={showA} onChange={(e) => setShowA(e.target.checked)} />
          <span className="inline-block h-2 w-2 rounded-full bg-brand-500" /> {labelA}
        </label>
        {!sameMetric && (
          <label className="flex cursor-pointer items-center gap-1.5 text-gray-600 dark:text-gray-300">
            <input type="checkbox" checked={showB} onChange={(e) => setShowB(e.target.checked)} />
            <span className="inline-block h-2 w-2 rounded-full bg-purple-500" /> {labelB}
          </label>
        )}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-100 dark:stroke-gray-800" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={30} />
          <YAxis yAxisId="a" tick={{ fontSize: 11 }} width={40} />
          <YAxis yAxisId="b" orientation="right" tick={{ fontSize: 11 }} width={40} />
          <Tooltip
            formatter={(value, name) => [
              formatHeadlineMetricValue(name === labelA ? metricA : metricB, value as number),
              name,
            ]}
            labelFormatter={(label) => label}
          />
          {showA && <Line yAxisId="a" type="monotone" dataKey={metricA} stroke="#465fff" strokeWidth={2} dot={false} name={labelA} />}
          {showB && !sameMetric && (
            <Line yAxisId="b" type="monotone" dataKey={metricB} stroke="#a855f7" strokeWidth={2} dot={false} name={labelB} />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function Ga4RealtimeRankedList({ title, rows }: { title: string; rows: { key: string; value: number }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
      <p className="mb-2 text-theme-xs font-semibold tracking-wide text-gray-400 uppercase">{title}</p>
      {rows.length === 0 ? (
        <p className="text-theme-xs text-gray-400">No data available</p>
      ) : (
        <div className="space-y-1.5">
          {rows.slice(0, 5).map((r, i) => (
            <div key={i} className="relative overflow-hidden rounded">
              <div
                className="absolute inset-y-0 left-0 bg-brand-50 dark:bg-brand-500/10"
                style={{ width: `${(r.value / max) * 100}%` }}
              />
              <div className="relative flex items-center justify-between gap-2 px-1.5 py-1 text-theme-xs">
                <span className="truncate text-gray-700 dark:text-gray-300">{r.key}</span>
                <span className="shrink-0 font-medium text-gray-900 dark:text-white">{r.value}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Ga4RealtimeOverviewPanel({ siteId }: { siteId: number }) {
  // Every query here polls every 30s — GA4 itself defines "realtime" as
  // the trailing ~30-minute window, so a snapshot older than that is
  // stale by the report's own definition.
  const minuteQuery = useQuery({
    queryKey: ["seo", "ga4-realtime-minute", siteId],
    queryFn: () => getGa4RealtimeByMinute(siteId),
    refetchInterval: 30_000,
  });
  const countryQuery = useQuery({
    queryKey: ["seo", "ga4-realtime-country", siteId],
    queryFn: () => getGa4Realtime(siteId),
    refetchInterval: 30_000,
  });
  const deviceQuery = useQuery({
    queryKey: ["seo", "ga4-realtime-device", siteId],
    queryFn: () => getGa4RealtimeByDevice(siteId),
    refetchInterval: 30_000,
  });
  const pageQuery = useQuery({
    queryKey: ["seo", "ga4-realtime-page", siteId],
    queryFn: () => getGa4RealtimeByPage(siteId),
    refetchInterval: 30_000,
  });
  const audienceQuery = useQuery({
    queryKey: ["seo", "ga4-realtime-audience", siteId],
    queryFn: () => getGa4RealtimeByAudience(siteId),
    refetchInterval: 30_000,
  });

  const minuteRows = minuteQuery.data ?? [];
  const byMinute = new Map(minuteRows.map((d) => [d.minutes_ago, d.active_users]));
  // Dense 30-slot series (minutesAgo 29 -> 0) — GA4 omits empty minutes
  // entirely rather than sending a zero row, so gaps are filled here to
  // match the real chart's own continuous bar-per-minute look.
  const chartData = Array.from({ length: 30 }, (_, i) => {
    const m = 29 - i;
    return { label: m === 0 ? "now" : `-${m} min`, activeUsers: byMinute.get(m) ?? 0 };
  });
  const active30 = minuteRows.reduce((sum, r) => sum + r.active_users, 0);
  const active5 = minuteRows.filter((r) => r.minutes_ago <= 4).reduce((sum, r) => sum + r.active_users, 0);

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success-500" />
          </span>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Realtime overview</h2>
        </div>

        {minuteQuery.isError ? (
          <p className="text-theme-sm text-error-500">{serverErrorDetail(minuteQuery.error, "GA4 realtime fetch failed.")}</p>
        ) : (
          <>
            <div className="mb-4 grid max-w-md grid-cols-2 gap-3">
              <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-theme-xs text-gray-400">Active users in last 30 minutes</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">{active30}</p>
              </div>
              <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-theme-xs text-gray-400">Active users in last 5 minutes</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">{active5}</p>
              </div>
            </div>

            <p className="mb-1 text-theme-xs font-semibold tracking-wide text-gray-400 uppercase">Active users per minute</p>
            {minuteQuery.isLoading ? (
              <div className="flex h-32 items-center justify-center text-gray-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <XAxis dataKey="label" tick={{ fontSize: 9 }} interval={4} />
                  <YAxis tick={{ fontSize: 11 }} width={28} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="activeUsers" name="Active users" fill="#465fff" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Ga4RealtimeRankedList
                title="By country"
                rows={(countryQuery.data ?? []).map((r) => ({ key: r.country, value: r.active_users }))}
              />
              <Ga4RealtimeRankedList
                title="By device"
                rows={(deviceQuery.data ?? []).map((r) => ({ key: formatGa4DimensionKey(r.key), value: r.value }))}
              />
              <Ga4RealtimeRankedList
                title="By audience"
                rows={(audienceQuery.data ?? []).map((r) => ({ key: r.key, value: r.value }))}
              />
              <Ga4RealtimeRankedList
                title="Views by page title"
                rows={(pageQuery.data ?? []).map((r) => ({ key: r.key, value: r.value }))}
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// A searchable, categorized dropdown matching GA4's own "Search items"
// metric picker (search box up top, items grouped by category below,
// the current selection highlighted) — see GA4_HEADLINE_METRICS above
// for why only User/Session/Event categories are offered.
function Ga4MetricPicker({
  value,
  onChange,
  triggerClassName,
}: {
  value: Ga4HeadlineMetricKey;
  onChange: (key: Ga4HeadlineMetricKey) => void;
  triggerClassName?: string;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const selected = GA4_HEADLINE_METRICS.find((m) => m.key === value)!;
  const query = search.trim().toLowerCase();
  const filtered = query ? GA4_HEADLINE_METRICS.filter((m) => m.label.toLowerCase().includes(query)) : null;
  const categories: (typeof GA4_HEADLINE_METRICS)[number]["category"][] = ["User", "Session", "Event"];

  const pick = (key: Ga4HeadlineMetricKey) => {
    onChange(key);
    setOpen(false);
    setSearch("");
  };

  const itemClass = (key: Ga4HeadlineMetricKey) =>
    `block w-full truncate rounded-md px-2 py-1.5 text-left text-theme-xs ${
      key === value
        ? "bg-brand-50 font-medium text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
        : "text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-white/5"
    }`;

  return (
    <div className="relative inline-block" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1 text-theme-xs font-medium ${triggerClassName ?? ""}`}
      >
        {selected.label}
        <ChevronDown className="h-3 w-3" />
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-64 rounded-lg border border-gray-200 bg-white p-2 text-left shadow-lg dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-2 flex items-center gap-2 rounded-md border border-gray-200 px-2 py-1.5 dark:border-gray-700">
            <Search className="h-3.5 w-3.5 shrink-0 text-gray-400" />
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search items"
              className="w-full bg-transparent text-theme-xs text-gray-700 outline-hidden dark:text-gray-300"
            />
          </div>
          <div className="max-h-64 overflow-y-auto">
            {filtered ? (
              filtered.length === 0 ? (
                <p className="px-2 py-1.5 text-theme-xs text-gray-400">No matches.</p>
              ) : (
                filtered.map((m) => (
                  <button key={m.key} type="button" onClick={() => pick(m.key)} className={itemClass(m.key)}>
                    {m.label}
                  </button>
                ))
              )
            ) : (
              categories.map((cat) => (
                <div key={cat} className="mb-2 last:mb-0">
                  <p className="px-2 py-1 text-theme-xs font-semibold tracking-wide text-gray-400 uppercase">{cat}</p>
                  {GA4_HEADLINE_METRICS.filter((m) => m.category === cat).map((m) => (
                    <button key={m.key} type="button" onClick={() => pick(m.key)} className={itemClass(m.key)}>
                      {m.label}
                    </button>
                  ))}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// One of the two switchable stat tiles in Ga4PerformancePanel's top
// row — each carries its own picker and its own % change vs the
// previous period, matching the real GA4 Home report's card carousel
// (picking a metric on one card never touches the other).
function Ga4HeadlineMetricCard({
  metric,
  onChange,
  value,
  pctChange,
  loading,
  colorClass,
  valueColorClass,
}: {
  metric: Ga4HeadlineMetricKey;
  onChange: (metric: Ga4HeadlineMetricKey) => void;
  value: number;
  pctChange: number | null;
  loading: boolean;
  colorClass: string;
  valueColorClass: string;
}) {
  return (
    <div className={`rounded-lg border p-3 ${colorClass}`}>
      <Ga4MetricPicker value={metric} onChange={onChange} triggerClassName="mb-1 text-inherit" />
      {loading ? (
        <div className="flex h-7 items-center text-gray-400">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      ) : (
        <div className="flex flex-wrap items-baseline gap-1.5">
          <p className={`text-xl font-semibold ${valueColorClass}`}>{formatHeadlineMetricValue(metric, value)}</p>
          {pctChange !== null && (
            <span
              className={`text-theme-xs font-medium ${pctChange >= 0 ? "text-success-600 dark:text-success-400" : "text-error-600 dark:text-error-400"}`}
            >
              {pctChange >= 0 ? "↑" : "↓"} {Math.abs(pctChange).toFixed(1)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function Ga4PerformancePanel({ siteId }: { siteId: number }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Ga4TabKey>("pages");
  const [rangeKey, setRangeKey] = useState<(typeof GA4_DATE_RANGES)[number]["key"]>("3m");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");

  const activeRange = GA4_DATE_RANGES.find((r) => r.key === rangeKey)!;
  const customReady = rangeKey === "custom" && !!customStart && !!customEnd;
  const filters: Ga4FilterParams =
    rangeKey === "custom"
      ? { startDate: customStart || undefined, endDate: customEnd || undefined }
      : { daysBack: activeRange.days ?? 90 };
  // Custom range isn't queryable until both dates are picked — every hook
  // below stays disabled rather than firing on a half-entered range.
  const rangeIsReady = rangeKey !== "custom" || customReady;

  const timeseriesQuery = useQuery({
    queryKey: ["seo", "ga4-timeseries", siteId, filters],
    queryFn: () => getGa4Timeseries(siteId, filters),
    enabled: rangeIsReady,
  });
  const timeseries = timeseriesQuery.data ?? [];
  const totals = timeseries.reduce(
    (acc, d) => ({ sessions: acc.sessions + d.sessions, conversions: acc.conversions + d.conversions, bounceWeighted: acc.bounceWeighted + d.bounce_rate * d.sessions }),
    { sessions: 0, conversions: 0, bounceWeighted: 0 }
  );
  const avgBounceRate = totals.sessions > 0 ? totals.bounceWeighted / totals.sessions : 0;
  const conversionRate = totals.sessions > 0 ? totals.conversions / totals.sessions : 0;

  // Two independently switchable metric cards, matching the real GA4
  // Home report's own card carousel (each card has its own "▾" dropdown
  // — picking a metric on one never changes the other). Defaulting to
  // Active users / New users per the actual request driving this.
  const [headlineMetricA, setHeadlineMetricA] = useState<Ga4HeadlineMetricKey>("active_users");
  const [headlineMetricB, setHeadlineMetricB] = useState<Ga4HeadlineMetricKey>("new_users");
  const previousFilters = getPreviousPeriodFilters(filters);
  const previousTimeseriesQuery = useQuery({
    queryKey: ["seo", "ga4-timeseries-previous", siteId, previousFilters],
    queryFn: () => getGa4Timeseries(siteId, previousFilters!),
    enabled: rangeIsReady && !!previousFilters,
  });
  const previousTimeseries = previousTimeseriesQuery.data ?? [];
  const pctChange = (current: number, previous: number) => (previous > 0 ? ((current - previous) / previous) * 100 : null);

  // Matches the real GA4 UI's own Home/Realtime "active users in the
  // last 30 minutes" tile — polled every 30s so it stays live without a
  // manual refresh, same trailing window GA4 itself uses.
  const realtimeQuery = useQuery({
    queryKey: ["seo", "ga4-realtime", siteId],
    queryFn: () => getGa4Realtime(siteId),
    refetchInterval: 30_000,
  });
  const realtimeRows = realtimeQuery.data ?? [];
  const realtimeTotal = realtimeRows.reduce((sum, r) => sum + r.active_users, 0);

  const pagesQuery = useQuery({
    queryKey: ["seo", "ga4-live-pages", siteId, filters],
    queryFn: () => getGa4PagesLive(siteId, filters),
    enabled: tab === "pages" && rangeIsReady,
  });
  const sourcesQuery = useQuery({
    queryKey: ["seo", "ga4-live-sources", siteId, filters],
    queryFn: () => getGa4BySource(siteId, filters),
    enabled: tab === "sources" && rangeIsReady,
  });
  const countriesQuery = useQuery({
    queryKey: ["seo", "ga4-live-countries", siteId, filters],
    queryFn: () => getGa4ByCountry(siteId, filters),
    enabled: tab === "countries" && rangeIsReady,
  });
  const devicesQuery = useQuery({
    queryKey: ["seo", "ga4-live-devices", siteId, filters],
    queryFn: () => getGa4ByDevice(siteId, filters),
    enabled: tab === "devices" && rangeIsReady,
  });

  const activeQuery = { pages: pagesQuery, sources: sourcesQuery, countries: countriesQuery, devices: devicesQuery }[tab];

  const rows: Ga4PerfRow[] =
    tab === "pages"
      ? (pagesQuery.data ?? []).map((r) => ({ label: r.page_path, sessions: r.sessions, bounceRate: r.bounce_rate, conversions: r.conversions }))
      : tab === "sources"
        ? (sourcesQuery.data ?? []).map((r) => ({ label: r.key, sessions: r.sessions, bounceRate: r.bounce_rate, conversions: r.conversions }))
        : tab === "countries"
          ? (countriesQuery.data ?? []).map((r) => ({ label: r.key, sessions: r.sessions, bounceRate: r.bounce_rate, conversions: r.conversions }))
          : (devicesQuery.data ?? []).map((r) => ({ label: formatGa4DimensionKey(r.key), sessions: r.sessions, bounceRate: r.bounce_rate, conversions: r.conversions }));

  const columnLabel = GA4_TABS.find((t) => t.key === tab)!.label.replace(/s$/, "");

  const dateRangeLabel =
    rangeKey === "custom" ? `Custom (${customStart || "?"} to ${customEnd || "?"})` : activeRange.label;

  const exportMutation = useMutation({
    // Fetches all 4 dimensions (not just whichever tab is on screen) so
    // one click writes Pages/Sources/Countries/Devices into their own
    // clean tabs — mirrors the GSC "Export All to Sheets" mutation above.
    mutationFn: async () => {
      const [pagesData, sourcesData, countriesData, devicesData] = await Promise.all([
        queryClient.fetchQuery({ queryKey: ["seo", "ga4-live-pages", siteId, filters], queryFn: () => getGa4PagesLive(siteId, filters) }),
        queryClient.fetchQuery({ queryKey: ["seo", "ga4-live-sources", siteId, filters], queryFn: () => getGa4BySource(siteId, filters) }),
        queryClient.fetchQuery({ queryKey: ["seo", "ga4-live-countries", siteId, filters], queryFn: () => getGa4ByCountry(siteId, filters) }),
        queryClient.fetchQuery({ queryKey: ["seo", "ga4-live-devices", siteId, filters], queryFn: () => getGa4ByDevice(siteId, filters) }),
      ]);
      return exportAllGa4ToSheet(siteId, dateRangeLabel, GA4_TABS.find((t) => t.key === tab)!.label, {
        pages: pagesData.map((r) => ({ label: r.page_path, sessions: r.sessions, bounce_rate: r.bounce_rate, conversions: r.conversions })),
        sources: sourcesData.map((r) => ({ label: r.key, sessions: r.sessions, bounce_rate: r.bounce_rate, conversions: r.conversions })),
        countries: countriesData.map((r) => ({ label: r.key, sessions: r.sessions, bounce_rate: r.bounce_rate, conversions: r.conversions })),
        devices: devicesData.map((r) => ({ label: formatGa4DimensionKey(r.key), sessions: r.sessions, bounce_rate: r.bounce_rate, conversions: r.conversions })),
        timeseries,
      });
    },
    onSuccess: (result) => {
      if (!result.ok) {
        toast.error(result.detail);
        return;
      }
      toast.success(result.detail);
      if (result.sheet_url) window.open(result.sheet_url, "_blank", "noopener,noreferrer");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Export to Sheets failed.")),
  });

  const downloadCsvMutation = useMutation({
    mutationFn: async () => {
      const [pagesData, sourcesData, countriesData, devicesData] = await Promise.all([
        queryClient.fetchQuery({ queryKey: ["seo", "ga4-live-pages", siteId, filters], queryFn: () => getGa4PagesLive(siteId, filters) }),
        queryClient.fetchQuery({ queryKey: ["seo", "ga4-live-sources", siteId, filters], queryFn: () => getGa4BySource(siteId, filters) }),
        queryClient.fetchQuery({ queryKey: ["seo", "ga4-live-countries", siteId, filters], queryFn: () => getGa4ByCountry(siteId, filters) }),
        queryClient.fetchQuery({ queryKey: ["seo", "ga4-live-devices", siteId, filters], queryFn: () => getGa4ByDevice(siteId, filters) }),
      ]);

      const toRow = (label: string, r: { sessions: number; bounce_rate: number; conversions: number }) => [
        label,
        String(r.sessions),
        `${(r.bounce_rate * 100).toFixed(1)}%`,
        String(r.conversions),
      ];
      const sections: { title: string; column: string; rows: string[][] }[] = [
        { title: "Pages", column: "Page", rows: pagesData.map((r) => toRow(r.page_path, r)) },
        { title: "Sources", column: "Source", rows: sourcesData.map((r) => toRow(r.key, r)) },
        { title: "Countries", column: "Country", rows: countriesData.map((r) => toRow(r.key, r)) },
        { title: "Devices", column: "Device", rows: devicesData.map((r) => toRow(formatGa4DimensionKey(r.key), r)) },
      ];

      const escape = (cell: string) => `"${cell.replace(/"/g, '""')}"`;
      const csv = sections
        .map((s) =>
          [
            escape(s.title),
            [s.column, "Sessions", "Bounce Rate", "Conversions"].map(escape).join(","),
            ...(s.rows.length ? s.rows.map((row) => row.map(escape).join(",")) : [escape("(no rows)")]),
          ].join("\r\n")
        )
        .join("\r\n\r\n");

      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ga4-all-${dateRangeLabel.replace(/[^a-z0-9]+/gi, "-")}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Download failed.")),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <BarChart3 className="h-4 w-4 text-brand-500" />
            Analytics Performance
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-white/5">
              {GA4_DATE_RANGES.map((r) => (
                <button
                  key={r.key}
                  onClick={() => setRangeKey(r.key)}
                  className={`rounded-md px-3 py-1 text-theme-xs font-medium transition-colors ${
                    rangeKey === r.key ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white" : "text-gray-500"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mb-4 rounded-lg border border-success-200 bg-success-50 p-3 dark:border-success-500/30 dark:bg-success-500/10">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-success-500" />
            </span>
            <p className="text-theme-sm font-medium text-success-700 dark:text-success-300">
              {realtimeQuery.isLoading
                ? "Checking active users…"
                : realtimeQuery.isError
                  ? serverErrorDetail(realtimeQuery.error, "Realtime fetch failed.")
                  : `${realtimeTotal.toLocaleString()} active user${realtimeTotal === 1 ? "" : "s"} right now`}
            </p>
          </div>
          {realtimeRows.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-theme-xs text-gray-500 dark:text-gray-400">
              {realtimeRows.slice(0, 8).map((r) => (
                <span key={r.country}>
                  {r.country}: {r.active_users}
                </span>
              ))}
            </div>
          )}
        </div>

        {rangeKey === "custom" && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Label htmlFor="ga4-custom-start" className="mb-0">
              From
            </Label>
            <Input id="ga4-custom-start" type="date" value={customStart} onChange={(e) => setCustomStart(e.target.value)} className="max-w-40" />
            <Label htmlFor="ga4-custom-end" className="mb-0">
              To
            </Label>
            <Input id="ga4-custom-end" type="date" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} className="max-w-40" />
            {!customReady && <span className="text-theme-xs text-gray-400">Pick both dates to load data.</span>}
          </div>
        )}

        {rangeIsReady && (
          <>
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Ga4HeadlineMetricCard
                metric={headlineMetricA}
                onChange={setHeadlineMetricA}
                value={computeHeadlineMetricValue(timeseries, headlineMetricA)}
                pctChange={pctChange(
                  computeHeadlineMetricValue(timeseries, headlineMetricA),
                  computeHeadlineMetricValue(previousTimeseries, headlineMetricA)
                )}
                loading={timeseriesQuery.isLoading}
                colorClass="border-brand-200 bg-brand-50 dark:border-brand-500/30 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300"
                valueColorClass="text-brand-800 dark:text-brand-200"
              />
              <Ga4HeadlineMetricCard
                metric={headlineMetricB}
                onChange={setHeadlineMetricB}
                value={computeHeadlineMetricValue(timeseries, headlineMetricB)}
                pctChange={pctChange(
                  computeHeadlineMetricValue(timeseries, headlineMetricB),
                  computeHeadlineMetricValue(previousTimeseries, headlineMetricB)
                )}
                loading={timeseriesQuery.isLoading}
                colorClass="border-purple-200 bg-purple-50 dark:border-purple-500/30 dark:bg-purple-500/10 text-purple-700 dark:text-purple-300"
                valueColorClass="text-purple-800 dark:text-purple-200"
              />
              <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-theme-xs text-gray-400">Avg. bounce rate</p>
                <p className="text-xl font-semibold text-gray-900 dark:text-white">{(avgBounceRate * 100).toFixed(1)}%</p>
              </div>
              <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <p className="text-theme-xs text-gray-400">Conversion rate</p>
                <p className="text-xl font-semibold text-gray-900 dark:text-white">{(conversionRate * 100).toFixed(1)}%</p>
              </div>
            </div>

            {timeseriesQuery.isLoading ? (
              <div className="mb-4 flex h-24 items-center justify-center text-gray-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : timeseriesQuery.isError ? (
              <p className="mb-4 text-theme-sm text-error-500">{serverErrorDetail(timeseriesQuery.error, "GA4 fetch failed.")}</p>
            ) : timeseries.length === 0 ? (
              <p className="mb-4 text-theme-sm text-gray-400">No data for this date range.</p>
            ) : (
              <div className="mb-4">
                <Ga4TrendChart data={timeseries} metricA={headlineMetricA} metricB={headlineMetricB} />
              </div>
            )}
          </>
        )}

        <div className="mb-3 flex flex-wrap gap-4 border-b border-gray-100 dark:border-gray-800">
          {GA4_TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`-mb-px border-b-2 pb-2 text-theme-xs font-semibold tracking-wide uppercase transition-colors ${
                tab === t.key
                  ? "border-brand-500 text-gray-900 dark:text-white"
                  : "border-transparent text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {!rangeIsReady ? null : activeQuery.isLoading ? (
          <div className="flex h-16 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : activeQuery.isError ? (
          <p className="text-theme-sm text-error-500">{serverErrorDetail(activeQuery.error, "GA4 fetch failed.")}</p>
        ) : rows.length === 0 ? (
          <p className="text-theme-sm text-gray-400">No rows for this view in the selected date range.</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="mb-2 flex justify-end gap-2">
              <Button size="sm" variant="outline" onClick={() => downloadCsvMutation.mutate()} disabled={downloadCsvMutation.isPending}>
                {downloadCsvMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                Download CSV
              </Button>
              <Button size="sm" variant="outline" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
                {exportMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                Export All to Sheets
              </Button>
            </div>
            <table className="w-full text-left text-theme-sm">
              <thead>
                <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                  <th className="py-2 pr-3 font-medium">{columnLabel}</th>
                  <th className="py-2 pr-3 font-medium">Sessions</th>
                  <th className="py-2 pr-3 font-medium">Bounce rate</th>
                  <th className="py-2 font-medium">Conversions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className="border-b border-gray-50 dark:border-gray-800/50">
                    <td className="max-w-xs truncate py-2 pr-3 text-gray-700 dark:text-gray-300">{r.label}</td>
                    <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{r.sessions}</td>
                    <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{(r.bounceRate * 100).toFixed(1)}%</td>
                    <td className="py-2 text-gray-500 dark:text-gray-400">{r.conversions}</td>
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

function SitemapsPanel({ siteId }: { siteId: number }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [feedpath, setFeedpath] = useState("sitemap.xml");

  const sitemapsQuery = useQuery({ queryKey: ["seo", "sitemaps", siteId], queryFn: () => getSitemaps(siteId) });
  const sitemaps = sitemapsQuery.data ?? [];

  const submitMutation = useMutation({
    mutationFn: () => submitSitemap(siteId, feedpath.trim()),
    onSuccess: (result) => {
      if (result.ok) {
        toast.success(result.detail);
        queryClient.invalidateQueries({ queryKey: ["seo", "sitemaps", siteId] });
      } else {
        toast.error(result.detail);
      }
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Sitemap submission failed.")),
  });

  const deleteMutation = useMutation({
    mutationFn: (path: string) => deleteSitemap(siteId, path),
    onSuccess: (result) => {
      if (result.ok) {
        toast.success(result.detail);
        queryClient.invalidateQueries({ queryKey: ["seo", "sitemaps", siteId] });
      } else {
        toast.error(result.detail);
      }
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Sitemap removal failed.")),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <FileText className="h-4 w-4 text-brand-500" />
          Sitemaps
        </h2>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
          Real Search Console sitemap tracking. Submitting/removing needs Full user or Owner access on this
          property in Search Console — a read-only (Restricted) user, enough for every other GSC feature here, will
          get a real permission error on those two actions.
        </p>
        <div className="flex flex-wrap gap-2">
          <Input value={feedpath} onChange={(e) => setFeedpath(e.target.value)} placeholder="sitemap.xml" className="max-w-xs" />
          <Button size="sm" onClick={() => submitMutation.mutate()} disabled={submitMutation.isPending || !feedpath.trim()}>
            {submitMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Submit
          </Button>
          <Button size="sm" variant="outline" onClick={() => sitemapsQuery.refetch()} disabled={sitemapsQuery.isFetching}>
            {sitemapsQuery.isFetching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Refresh
          </Button>
        </div>

        {sitemapsQuery.isLoading ? (
          <div className="mt-4 flex h-16 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : sitemapsQuery.isError ? (
          <p className="mt-4 text-theme-sm text-error-500">{serverErrorDetail(sitemapsQuery.error, "Sitemaps fetch failed.")}</p>
        ) : sitemaps.length === 0 ? (
          <p className="mt-4 text-theme-sm text-gray-400">No sitemaps submitted for this property yet.</p>
        ) : (
          <div className="mt-4 space-y-2">
            {sitemaps.map((s) => (
              <div key={s.path} className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="break-all text-theme-sm font-medium text-gray-900 dark:text-white">{s.path}</p>
                  <Button size="sm" variant="outline" onClick={() => deleteMutation.mutate(s.path)} disabled={deleteMutation.isPending}>
                    <XCircle className="h-3.5 w-3.5" />
                    Remove
                  </Button>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {s.is_pending && <Badge variant="warning">pending</Badge>}
                  {s.is_sitemaps_index && <Badge variant="outline">sitemap index</Badge>}
                  {typeof s.warnings === "number" && s.warnings > 0 && <Badge variant="warning">{s.warnings} warning(s)</Badge>}
                  {typeof s.errors === "number" && s.errors > 0 && <Badge variant="destructive">{s.errors} error(s)</Badge>}
                </div>
                {s.contents.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-3 text-theme-xs text-gray-500 dark:text-gray-400">
                    {s.contents.map((c, i) => (
                      <span key={i}>
                        {c.type}: {c.indexed ?? 0}/{c.submitted ?? 0} indexed
                      </span>
                    ))}
                  </div>
                )}
                <p className="mt-1 text-theme-xs text-gray-400">
                  {s.last_submitted ? `Submitted ${s.last_submitted}` : "Not submitted"}
                  {s.last_downloaded ? ` · last downloaded ${s.last_downloaded}` : ""}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SiteVerificationPanel() {
  const verificationQuery = useQuery({ queryKey: ["seo", "site-verification"], queryFn: getVerifiedSites });
  const sites = verificationQuery.data ?? [];

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <CheckCircle2 className="h-4 w-4 text-brand-500" />
            Site Verification
          </h2>
          <Button size="sm" variant="outline" onClick={() => verificationQuery.refetch()} disabled={verificationQuery.isFetching}>
            {verificationQuery.isFetching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Refresh
          </Button>
        </div>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
          Properties this Google service account has itself verified ownership of — a separate Google permission
          system from being added as a Search Console user (which is how every other GSC feature here works).
        </p>
        {verificationQuery.isLoading ? (
          <div className="flex h-16 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : verificationQuery.isError ? (
          <p className="text-theme-sm text-error-500">
            {serverErrorDetail(verificationQuery.error, "Site Verification API call failed.")}
          </p>
        ) : sites.length === 0 ? (
          <p className="text-theme-sm text-gray-400">
            No verified sites for this service account (expected — this app connects sites by adding the service
            account as a Search Console user, not by having it perform its own verification).
          </p>
        ) : (
          <div className="space-y-2">
            {sites.map((s) => (
              <div key={s.id} className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <p className="break-all text-theme-sm font-medium text-gray-900 dark:text-white">{s.identifier ?? s.id}</p>
                <div className="mt-1 flex flex-wrap gap-2">
                  {s.type && <Badge variant="outline">{s.type}</Badge>}
                  {s.owners.map((o) => (
                    <Badge key={o} variant="outline">
                      {o}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
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

  // "Request again" on a specific inspected URL's own card — separate
  // from the form above's submitMutation so clicking it doesn't touch
  // whatever the human currently has typed into that form's input.
  const requestIndexingMutation = useMutation({
    mutationFn: (url: string) => submitForIndexing(siteId, url, "URL_UPDATED"),
    onSuccess: (result) => {
      if (result.success) toast.success("Submitted to Google's Indexing API.");
      else toast.info(result.error || "Submission failed — see the log below.");
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
              {statuses.map((s) => {
                const isIndexed = !!s.coverage_state?.toLowerCase().includes("indexed") && !s.coverage_state?.toLowerCase().includes("not");
                const lastSubmission = submissions
                  .filter((sub) => sub.url === s.url && sub.success)
                  .sort((a, b) => (b.submitted_at ?? "").localeCompare(a.submitted_at ?? ""))[0];
                let sitemapList: string[] = [];
                try {
                  sitemapList = s.sitemap_json ? JSON.parse(s.sitemap_json) : [];
                } catch {
                  sitemapList = [];
                }

                return (
                  <div key={s.id} className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="break-all text-theme-sm font-medium text-gray-900 dark:text-white">{s.url}</p>
                      {s.inspection_result_link && (
                        <a
                          href={s.inspection_result_link}
                          target="_blank"
                          rel="noreferrer"
                          className="shrink-0 text-theme-xs text-brand-600 hover:underline dark:text-brand-400"
                        >
                          Open in Search Console
                        </a>
                      )}
                    </div>

                    <div className="mt-2 flex items-center gap-2">
                      {isIndexed ? (
                        <CheckCircle2 className="h-4 w-4 text-success-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-warning-500" />
                      )}
                      <p className="text-theme-sm font-semibold text-gray-900 dark:text-white">
                        {isIndexed ? "URL is on Google" : "URL is not on Google"}
                      </p>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-2">
                      <Badge variant={isIndexed ? "success" : "outline"}>{s.coverage_state ?? "unknown"}</Badge>
                      {s.indexing_state && <Badge variant="outline">{s.indexing_state}</Badge>}
                      {s.robots_txt_state && <Badge variant="outline">robots.txt: {s.robots_txt_state}</Badge>}
                      {s.page_fetch_state && <Badge variant="outline">fetch: {s.page_fetch_state}</Badge>}
                      {s.mobile_usability_verdict && s.mobile_usability_verdict !== "VERDICT_UNSPECIFIED" && (
                        <Badge variant={s.mobile_usability_verdict === "PASS" ? "success" : "outline"}>
                          mobile: {s.mobile_usability_verdict}
                        </Badge>
                      )}
                    </div>

                    <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-gray-100 pt-3 dark:border-gray-800">
                      {lastSubmission ? (
                        <span className="flex items-center gap-1 text-theme-xs text-gray-500 dark:text-gray-400">
                          <CheckCircle2 className="h-3.5 w-3.5 text-success-500" />
                          Indexing requested {lastSubmission.submitted_at}
                        </span>
                      ) : (
                        <span className="text-theme-xs text-gray-400">Not yet requested for indexing</span>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => requestIndexingMutation.mutate(s.url)}
                        disabled={requestIndexingMutation.isPending}
                      >
                        {requestIndexingMutation.isPending ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Send className="h-3.5 w-3.5" />
                        )}
                        {lastSubmission ? "Request again" : "Request indexing"}
                      </Button>
                    </div>

                    <div className="mt-3 border-t border-gray-100 pt-3 dark:border-gray-800">
                      <p className="text-theme-xs font-semibold text-gray-500 dark:text-gray-400">Discovery</p>
                      <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">
                        {sitemapList.length > 0 ? `Referenced in: ${sitemapList.join(", ")}` : "No referring sitemaps detected"}
                      </p>
                    </div>

                    <div className="mt-3 border-t border-gray-100 pt-3 dark:border-gray-800">
                      <p className="text-theme-xs font-semibold text-gray-500 dark:text-gray-400">Crawl</p>
                      <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">
                        {s.last_crawl_time ? `Last crawled ${s.last_crawl_time}` : "Never crawled by Google"}
                        {s.crawled_as ? ` · crawled as ${s.crawled_as.charAt(0)}${s.crawled_as.slice(1).toLowerCase()}` : ""}
                      </p>
                      {s.google_canonical && (
                        <p className="mt-1 break-all text-theme-xs text-gray-500 dark:text-gray-400">
                          Google-selected canonical: {s.google_canonical}
                        </p>
                      )}
                      {s.user_canonical && s.user_canonical !== s.google_canonical && (
                        <p className="mt-1 break-all text-theme-xs text-gray-500 dark:text-gray-400">
                          User-declared canonical: {s.user_canonical}
                        </p>
                      )}
                    </div>

                    <p className="mt-2 text-theme-xs text-gray-400">checked {s.checked_at}</p>
                  </div>
                );
              })}
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

// Module 55 — GA4's own "Events: Event name" report (Life cycle >
// Engagement > Events in the real GA4 UI). Its own date-range state,
// separate from Ga4PerformancePanel above, same as every other GA4/GSC
// panel on this page. The real report also lets a human tick rows to
// plot them on a chart above the table — left out here since it's a
// secondary interaction on top of the core "see every event with its
// real numbers" ask this panel already delivers.
function Ga4EventsPanel({ siteId }: { siteId: number }) {
  const toast = useToast();
  const [rangeKey, setRangeKey] = useState<(typeof GA4_DATE_RANGES)[number]["key"]>("7d");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [search, setSearch] = useState("");

  const activeRange = GA4_DATE_RANGES.find((r) => r.key === rangeKey)!;
  const customReady = rangeKey === "custom" && !!customStart && !!customEnd;
  const filters: Ga4FilterParams =
    rangeKey === "custom"
      ? { startDate: customStart || undefined, endDate: customEnd || undefined }
      : { daysBack: activeRange.days ?? 7 };
  const rangeIsReady = rangeKey !== "custom" || customReady;
  const dateRangeLabel = rangeKey === "custom" ? `Custom (${customStart || "?"} to ${customEnd || "?"})` : activeRange.label;

  const eventsQuery = useQuery({
    queryKey: ["seo", "ga4-events", siteId, filters],
    queryFn: () => getGa4Events(siteId, filters),
    enabled: rangeIsReady,
  });
  const events = eventsQuery.data ?? [];
  const query = search.trim().toLowerCase();
  const rows = query ? events.filter((e) => e.event_name.toLowerCase().includes(query)) : events;
  const totalEventCount = events.reduce((sum, e) => sum + e.event_count, 0);

  // Its own dedicated "GA4 Events" tab — separate from Ga4PerformancePanel's
  // own "Export All to Sheets" (Pages/Sources/Countries/Devices), which
  // never fetched event data and so never had anything to write here.
  const exportMutation = useMutation({
    mutationFn: () =>
      exportAllGa4ToSheet(siteId, dateRangeLabel, "Events", {
        events: events.map((e) => ({
          event_name: e.event_name,
          event_count: e.event_count,
          total_users: e.total_users,
          event_count_per_active_user: e.event_count_per_active_user,
          total_revenue: e.total_revenue,
        })),
      }),
    onSuccess: (result) => {
      if (!result.ok) {
        toast.error(result.detail);
        return;
      }
      toast.success(result.detail);
      if (result.sheet_url) window.open(result.sheet_url, "_blank", "noopener,noreferrer");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Export to Sheets failed.")),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <Hash className="h-4 w-4 text-brand-500" />
            Events
          </h2>
          <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-white/5">
            {GA4_DATE_RANGES.map((r) => (
              <button
                key={r.key}
                onClick={() => setRangeKey(r.key)}
                className={`rounded-md px-3 py-1 text-theme-xs font-medium transition-colors ${
                  rangeKey === r.key ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white" : "text-gray-500"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {rangeKey === "custom" && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Label htmlFor="ga4-events-custom-start" className="mb-0">
              From
            </Label>
            <Input id="ga4-events-custom-start" type="date" value={customStart} onChange={(e) => setCustomStart(e.target.value)} className="max-w-40" />
            <Label htmlFor="ga4-events-custom-end" className="mb-0">
              To
            </Label>
            <Input id="ga4-events-custom-end" type="date" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} className="max-w-40" />
            {!customReady && <span className="text-theme-xs text-gray-400">Pick both dates to load data.</span>}
          </div>
        )}

        {!rangeIsReady ? null : eventsQuery.isLoading ? (
          <div className="flex h-24 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : eventsQuery.isError ? (
          <p className="text-theme-sm text-error-500">{serverErrorDetail(eventsQuery.error, "GA4 events fetch failed.")}</p>
        ) : events.length === 0 ? (
          <p className="text-theme-sm text-gray-400">No events recorded for this date range.</p>
        ) : (
          <>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div className="relative max-w-xs flex-1">
                <Search className="absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search events…"
                  className="pl-8"
                />
              </div>
              <div className="flex items-center gap-3">
                <p className="text-theme-xs text-gray-400">
                  {events.length} event type{events.length === 1 ? "" : "s"} · {totalEventCount.toLocaleString()} total events
                </p>
                <Button size="sm" variant="outline" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
                  {exportMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                  Export to Sheets
                </Button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-theme-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                    <th className="py-2 pr-3 font-medium">Event name</th>
                    <th className="py-2 pr-3 font-medium">Event count</th>
                    <th className="py-2 pr-3 font-medium">Total users</th>
                    <th className="py-2 pr-3 font-medium">Event count per active user</th>
                    <th className="py-2 font-medium">Total revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-4 text-theme-sm text-gray-400">
                        No events match "{search}".
                      </td>
                    </tr>
                  ) : (
                    rows.map((e) => (
                      <tr key={e.event_name} className="border-b border-gray-50 dark:border-gray-800/50">
                        <td className="max-w-xs truncate py-2 pr-3 font-medium text-gray-900 dark:text-white">{e.event_name}</td>
                        <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{e.event_count.toLocaleString()}</td>
                        <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{e.total_users.toLocaleString()}</td>
                        <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{e.event_count_per_active_user.toFixed(2)}</td>
                        <td className="py-2 text-gray-500 dark:text-gray-400">${e.total_revenue.toFixed(2)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// Search Console gets its own tab (Module 53) — previously bundled into
// the Indexing tab alongside GA4 and the Indexing tab's own index-
// coverage/submission tools, which made one tab do three unrelated
// jobs. Performance dashboard + sitemap management + site verification
// are all genuinely "Search Console" concerns, so they move together.
function SearchConsoleTab({ siteId }: { siteId: number }) {
  return (
    <>
      <GscPerformancePanel siteId={siteId} />
      <SitemapsPanel siteId={siteId} />
      <SiteVerificationPanel />
    </>
  );
}

// Analytics (GA4) gets its own tab (Module 53) — same split as
// SearchConsoleTab above, just for the GA4 side of what used to be
// crammed into Indexing.
function Ga4Tab({ siteId }: { siteId: number }) {
  return (
    <>
      <Ga4PerformancePanel siteId={siteId} />
      <Ga4EventsPanel siteId={siteId} />
      <Ga4RealtimeOverviewPanel siteId={siteId} />
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

// Module 37 — "Semrush Magic Tool" on RapidAPI, verified live returning
// real keyword research data (search volume, CPC, competition, intent,
// monetization scoring) for hundreds of related keywords per seed
// keyword. A different, working product from the broken one below.
function KeywordResearchCard() {
  const toast = useToast();
  const [keyword, setKeyword] = useState("");
  const [country, setCountry] = useState("us");
  const [rows, setRows] = useState<KeywordResearchRow[] | null>(null);

  const researchMutation = useMutation({
    mutationFn: () => researchKeywords(keyword.trim(), "en", country),
    onSuccess: (data) => {
      setRows([...data].sort((a, b) => (b.avg_monthly_searches ?? 0) - (a.avg_monthly_searches ?? 0)));
      toast.success(`Found ${data.length} related keyword(s).`);
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Keyword research failed.")),
  });

  const shown = rows?.slice(0, 50) ?? [];

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Search className="h-4 w-4 text-brand-500" />
          Keyword Research
        </h2>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
          Search volume, CPC, competition, and intent for a seed keyword and hundreds of related/long-tail
          variations. Third-party data source (not Semrush's own official API).
        </p>
        <div className="flex flex-wrap gap-2">
          <Input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="Seed keyword, e.g. seo automation"
            className="max-w-sm"
          />
          <Input value={country} onChange={(e) => setCountry(e.target.value)} placeholder="Country" className="max-w-20" />
          <Button size="sm" onClick={() => researchMutation.mutate()} disabled={researchMutation.isPending || !keyword.trim()}>
            {researchMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Research
          </Button>
        </div>
        {researchMutation.isPending && (
          <p className="mt-2 text-theme-xs text-gray-400">This can take up to a minute…</p>
        )}
        {rows && (
          <div className="mt-3 overflow-x-auto">
            {rows.length > 50 && (
              <p className="mb-2 text-theme-xs text-gray-400">Showing top 50 of {rows.length} by search volume.</p>
            )}
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                  <th className="pb-2 pr-4 font-medium">Keyword</th>
                  <th className="pb-2 pr-4 font-medium">Avg. Monthly Searches</th>
                  <th className="pb-2 pr-4 font-medium">CPC</th>
                  <th className="pb-2 pr-4 font-medium">Competition</th>
                  <th className="pb-2 pr-4 font-medium">Intent</th>
                  <th className="pb-2 font-medium">Monetization</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((row, idx) => (
                  <tr key={idx} className="border-b border-gray-50 last:border-0 dark:border-gray-800/50">
                    <td className="py-2 pr-4 text-theme-sm text-gray-700 dark:text-gray-300">{row.keyword}</td>
                    <td className="py-2 pr-4 text-theme-sm text-gray-500 dark:text-gray-400">
                      {row.avg_monthly_searches ?? "—"}
                    </td>
                    <td className="py-2 pr-4 text-theme-xs text-gray-400">
                      {row.low_cpc ?? "—"}–{row.high_cpc ?? "—"}
                    </td>
                    <td className="py-2 pr-4">
                      <Badge
                        variant={
                          row.competition_value === "low" ? "success" : row.competition_value === "high" ? "destructive" : "warning"
                        }
                      >
                        {row.competition_value ?? "—"} {row.competition_index != null && `(${row.competition_index})`}
                      </Badge>
                    </td>
                    <td className="py-2 pr-4 text-theme-xs text-gray-500 dark:text-gray-400">{row.intent.join(", ") || "—"}</td>
                    <td className="py-2 text-theme-sm text-gray-500 dark:text-gray-400">
                      {row.monetization_score != null ? row.monetization_score.toFixed(1) : "—"}
                    </td>
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

// A THIRD distinct RapidAPI product/host (semrush-seo10), same
// application/key as KeywordResearchCard above — verified live
// returning real difficulty score, volume, competition, CPC, and a
// monthly trend for one specific keyword (a quick single-keyword check,
// complementing KeywordResearchCard's hundreds-of-related-keywords view).
function KeywordDifficultyCard() {
  const toast = useToast();
  const [keyword, setKeyword] = useState("");
  const [country, setCountry] = useState("us");
  const [result, setResult] = useState<KeywordDifficulty | null>(null);

  const checkMutation = useMutation({
    mutationFn: () => checkKeywordDifficulty(keyword.trim(), country),
    onSuccess: (data) => {
      setResult(data);
      toast.success("Difficulty check complete.");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "Keyword difficulty check failed.")),
  });

  const difficulty = result?.keyword_difficulty ?? null;
  const difficultyTone = difficulty == null ? "neutral" : difficulty < 34 ? "success" : difficulty < 67 ? "warning" : "error";

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Gauge className="h-4 w-4 text-brand-500" />
          Keyword Difficulty
        </h2>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
          Quick single-keyword check: difficulty score (0-100), volume, competition, and CPC.
        </p>
        <div className="flex flex-wrap gap-2">
          <Input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="Keyword" className="max-w-sm" />
          <Input value={country} onChange={(e) => setCountry(e.target.value)} placeholder="Country" className="max-w-20" />
          <Button size="sm" onClick={() => checkMutation.mutate()} disabled={checkMutation.isPending || !keyword.trim()}>
            {checkMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Check
          </Button>
        </div>
        {result && (
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-md border border-gray-100 p-3 dark:border-gray-800">
              <p className="text-theme-xs text-gray-400">Difficulty</p>
              <p
                className={`text-lg font-semibold ${
                  difficultyTone === "success"
                    ? "text-success-600 dark:text-success-400"
                    : difficultyTone === "warning"
                    ? "text-warning-600 dark:text-warning-400"
                    : difficultyTone === "error"
                    ? "text-error-600 dark:text-error-400"
                    : "text-gray-400"
                }`}
              >
                {difficulty ?? "—"}
              </p>
            </div>
            <div className="rounded-md border border-gray-100 p-3 dark:border-gray-800">
              <p className="text-theme-xs text-gray-400">Volume</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{result.volume ?? "—"}</p>
            </div>
            <div className="rounded-md border border-gray-100 p-3 dark:border-gray-800">
              <p className="text-theme-xs text-gray-400">Competition</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{result.competition ?? "—"}</p>
            </div>
            <div className="rounded-md border border-gray-100 p-3 dark:border-gray-800">
              <p className="text-theme-xs text-gray-400">CPC</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {result.cpc_dollars != null ? `$${result.cpc_dollars}` : "—"}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Module 37 — a third-party RapidAPI keyword wrapper (NOT Semrush's own
// official API), added as a cheaper alternative for keyword research.
// Every live test this session returned the provider's own generic
// error, not real data, so this shows the raw response as-is (unknown
// shape) rather than a polished table — tighten this once a real
// successful response has actually been observed.
function RapidApiKeywordCard({ siteId }: { siteId: number }) {
  const toast = useToast();
  const [country, setCountry] = useState("us");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  const checkMutation = useMutation({
    mutationFn: () => checkRapidApiKeywords(siteId, country),
    onSuccess: (data) => {
      setResult(data);
      toast.success("Response received — see raw result below.");
    },
    onError: (err) => toast.error(serverErrorDetail(err, "RapidAPI keyword check failed.")),
  });

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Search className="h-4 w-4 text-brand-500" />
          Domain Keyword Check (RapidAPI, currently unavailable)
        </h2>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
          A different third-party provider than the Keyword Research tool above. Live testing found this
          provider's backend returning errors even for well-known domains — shown as raw data below in case
          that changes.
        </p>
        <div className="flex flex-wrap gap-2">
          <Input value={country} onChange={(e) => setCountry(e.target.value)} placeholder="Country code" className="max-w-24" />
          <Button size="sm" onClick={() => checkMutation.mutate()} disabled={checkMutation.isPending}>
            {checkMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Check
          </Button>
        </div>
        {checkMutation.isPending && (
          <p className="mt-2 text-theme-xs text-gray-400">This provider can take up to a minute to respond…</p>
        )}
        {result && (
          <pre className="mt-3 max-h-64 overflow-auto rounded-md border border-gray-200 bg-gray-50 p-3 text-theme-xs text-gray-700 dark:border-gray-800 dark:bg-white/5 dark:text-gray-300">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}

function TopBacklinksCard({ siteId, siteUrl }: { siteId: number; siteUrl: string }) {
  const toast = useToast();
  const [website, setWebsite] = useState(siteUrl);

  const checkMutation = useMutation({
    mutationFn: () => getTopBacklinks(siteId, website.trim()),
    onError: (err) => toast.error(serverErrorDetail(err, "Top backlinks check failed.")),
  });
  const rows = checkMutation.data ?? [];

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Link2 className="h-4 w-4 text-brand-500" />
          Top Backlinks (RapidAPI)
        </h2>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
          Real page-level backlinks for any domain — source URL, anchor text, follow/nofollow, and spam score. Works
          for competitor domains too, not just your own.
        </p>
        <div className="flex flex-wrap gap-2">
          <Input value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://example.com" className="max-w-sm" />
          <Button size="sm" onClick={() => checkMutation.mutate()} disabled={checkMutation.isPending || !website.trim()}>
            {checkMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Check
          </Button>
        </div>
        {rows.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <p className="mb-2 text-theme-xs text-gray-400">{rows.length} backlink(s) found</p>
            <table className="w-full text-left text-theme-sm">
              <thead>
                <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                  <th className="py-2 pr-3 font-medium">Source</th>
                  <th className="py-2 pr-3 font-medium">Anchor</th>
                  <th className="py-2 pr-3 font-medium">Follow</th>
                  <th className="py-2 pr-3 font-medium">Rank</th>
                  <th className="py-2 pr-3 font-medium">Spam</th>
                  <th className="py-2 font-medium">First seen</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 50).map((r, i) => (
                  <tr key={i} className="border-b border-gray-50 dark:border-gray-800/50">
                    <td className="max-w-xs truncate py-2 pr-3" title={r.url_from}>
                      <a href={r.url_from} target="_blank" rel="noreferrer" className="text-brand-600 hover:underline dark:text-brand-400">
                        {r.url_from}
                      </a>
                    </td>
                    <td className="max-w-[160px] truncate py-2 pr-3 text-gray-500 dark:text-gray-400" title={r.anchor}>
                      {r.anchor || "—"}
                    </td>
                    <td className="py-2 pr-3">
                      <Badge variant={r.nofollow ? "outline" : "success"}>{r.nofollow ? "nofollow" : "follow"}</Badge>
                    </td>
                    <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{r.inlink_rank ?? "—"}</td>
                    <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{r.spam_score ?? "—"}</td>
                    <td className="py-2 text-gray-500 dark:text-gray-400">{r.first_seen || "—"}</td>
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

function DomainAuthorityCard({ siteId, siteUrl }: { siteId: number; siteUrl: string }) {
  const toast = useToast();
  const [website, setWebsite] = useState(siteUrl);
  const [bulkInput, setBulkInput] = useState("");

  const checkMutation = useMutation({
    mutationFn: () => getDomainAuthority(siteId, website.trim()),
    onError: (err) => toast.error(serverErrorDetail(err, "Domain authority check failed.")),
  });

  const bulkMutation = useMutation({
    mutationFn: (domains: string[]) => getBulkDomainAuthority(siteId, domains),
    onError: (err) => toast.error(serverErrorDetail(err, "Bulk domain authority check failed.")),
  });

  const handleBulk = () => {
    const domains = bulkInput.split(",").map((d) => d.trim()).filter(Boolean);
    if (domains.length === 0) {
      toast.error("Enter at least one domain.");
      return;
    }
    bulkMutation.mutate(domains);
  };

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Award className="h-4 w-4 text-brand-500" />
          DA / PA Checker (RapidAPI)
        </h2>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
          Domain Authority, Page Authority, spam score, Domain Rating, and estimated organic traffic for one domain,
          or several at once below.
        </p>
        <div className="flex flex-wrap gap-2">
          <Input value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://example.com" className="max-w-sm" />
          <Button size="sm" onClick={() => checkMutation.mutate()} disabled={checkMutation.isPending || !website.trim()}>
            {checkMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Check
          </Button>
        </div>
        {checkMutation.data && (
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
            <div>
              <p className="text-theme-xs text-gray-400">DA</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{checkMutation.data.da ?? "—"}</p>
            </div>
            <div>
              <p className="text-theme-xs text-gray-400">PA</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{checkMutation.data.pa ?? "—"}</p>
            </div>
            <div>
              <p className="text-theme-xs text-gray-400">Domain Rating</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{checkMutation.data.dr ?? "—"}</p>
            </div>
            <div>
              <p className="text-theme-xs text-gray-400">Spam score</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{checkMutation.data.spam_score ?? "—"}</p>
            </div>
            <div>
              <p className="text-theme-xs text-gray-400">Est. org. traffic</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{checkMutation.data.org_traffic ?? "—"}</p>
            </div>
          </div>
        )}

        <div className="mt-5 border-t border-gray-100 pt-4 dark:border-gray-800">
          <p className="mb-2 text-theme-xs font-medium text-gray-500 dark:text-gray-400">Bulk check</p>
          <div className="flex flex-wrap gap-2">
            <Input
              value={bulkInput}
              onChange={(e) => setBulkInput(e.target.value)}
              placeholder="domain1.com, domain2.com, domain3.com"
              className="max-w-md"
            />
            <Button size="sm" variant="outline" onClick={handleBulk} disabled={bulkMutation.isPending}>
              {bulkMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              Check all
            </Button>
          </div>
          {bulkMutation.data && bulkMutation.data.length > 0 && (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-theme-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                    <th className="py-2 pr-3 font-medium">Domain</th>
                    <th className="py-2 pr-3 font-medium">DA</th>
                    <th className="py-2 pr-3 font-medium">PA</th>
                    <th className="py-2 pr-3 font-medium">DR</th>
                    <th className="py-2 pr-3 font-medium">Spam</th>
                    <th className="py-2 font-medium">Est. traffic</th>
                  </tr>
                </thead>
                <tbody>
                  {bulkMutation.data.map((d) => (
                    <tr key={d.domain} className="border-b border-gray-50 dark:border-gray-800/50">
                      <td className="py-2 pr-3 text-gray-700 dark:text-gray-300">{d.domain}</td>
                      <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{d.da ?? "—"}</td>
                      <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{d.pa ?? "—"}</td>
                      <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{d.dr ?? "—"}</td>
                      <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{d.spam_score ?? "—"}</td>
                      <td className="py-2 text-gray-500 dark:text-gray-400">{d.org_traffic ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function KeywordInsightsCard() {
  const toast = useToast();
  const [keyword, setKeyword] = useState("");
  const [country, setCountry] = useState("us");

  const checkMutation = useMutation({
    mutationFn: () => getKeywordInsights(keyword.trim(), country.trim() || "us"),
    onError: (err) => toast.error(serverErrorDetail(err, "Keyword insights check failed.")),
  });
  const data = checkMutation.data;

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <Search className="h-4 w-4 text-brand-500" />
          Keyword Insights (RapidAPI)
        </h2>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
          Search volume, CPC, competition, and search intent for one keyword.
        </p>
        <div className="flex flex-wrap gap-2">
          <Input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="Keyword" className="max-w-xs" />
          <Input value={country} onChange={(e) => setCountry(e.target.value)} placeholder="Country code" className="max-w-24" />
          <Button size="sm" onClick={() => checkMutation.mutate()} disabled={checkMutation.isPending || !keyword.trim()}>
            {checkMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Check
          </Button>
        </div>
        {data && (
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div>
              <p className="text-theme-xs text-gray-400">Volume</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{data.volume ?? "—"}</p>
            </div>
            <div>
              <p className="text-theme-xs text-gray-400">Competition</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{data.competition ?? "—"}</p>
            </div>
            <div>
              <p className="text-theme-xs text-gray-400">CPC</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{data.cpc_dollars != null ? `$${data.cpc_dollars}` : "—"}</p>
            </div>
            <div>
              <p className="text-theme-xs text-gray-400">Difficulty</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">{data.sd ?? "—"}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function WebsiteTrafficCard({ siteId, siteUrl }: { siteId: number; siteUrl: string }) {
  const toast = useToast();
  const [website, setWebsite] = useState(siteUrl);

  const checkMutation = useMutation({
    mutationFn: () => getWebsiteTraffic(siteId, website.trim()),
    onError: (err) => toast.error(serverErrorDetail(err, "Website traffic check failed.")),
  });
  const data = checkMutation.data;

  return (
    <Card>
      <CardContent className="p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
          <TrendingUp className="h-4 w-4 text-brand-500" />
          Check Website Traffic (RapidAPI)
        </h2>
        <p className="mb-3 text-theme-sm text-gray-500 dark:text-gray-400">
          Estimated organic traffic, ranked-keyword count, ranking-position distribution, and real sample keywords
          for any domain.
        </p>
        <div className="flex flex-wrap gap-2">
          <Input value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://example.com" className="max-w-sm" />
          <Button size="sm" onClick={() => checkMutation.mutate()} disabled={checkMutation.isPending || !website.trim()}>
            {checkMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Check
          </Button>
        </div>
        {data && (
          <>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <p className="text-theme-xs text-gray-400">Est. organic traffic</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">{data.organic_etv ?? "—"}</p>
              </div>
              <div>
                <p className="text-theme-xs text-gray-400">Organic keywords</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">{data.organic_keywords ?? "—"}</p>
              </div>
              <div>
                <p className="text-theme-xs text-gray-400">Ranked keywords</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">{data.ranked_keywords_total ?? "—"}</p>
              </div>
              <div>
                <p className="text-theme-xs text-gray-400">Est. paid traffic cost</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {data.estimated_paid_traffic_cost != null ? `$${data.estimated_paid_traffic_cost}` : "—"}
                </p>
              </div>
            </div>
            {Object.keys(data.position_distribution).length > 0 && (
              <div className="mt-3 flex flex-wrap gap-3 text-theme-xs text-gray-500 dark:text-gray-400">
                {Object.entries(data.position_distribution).map(([pos, count]) => (
                  <span key={pos}>
                    {pos.replace("pos_", "#")}: <span className="font-medium text-gray-700 dark:text-gray-300">{count}</span>
                  </span>
                ))}
              </div>
            )}
            {data.sample_keywords.length > 0 && (
              <div className="mt-4 overflow-x-auto">
                <p className="mb-2 text-theme-xs text-gray-400">Sample ranking keywords</p>
                <table className="w-full text-left text-theme-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-theme-xs text-gray-400 dark:border-gray-800">
                      <th className="py-2 pr-3 font-medium">Keyword</th>
                      <th className="py-2 pr-3 font-medium">Position</th>
                      <th className="py-2 pr-3 font-medium">Volume</th>
                      <th className="py-2 pr-3 font-medium">CPC</th>
                      <th className="py-2 font-medium">Ranking page</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.sample_keywords.map((k, i) => (
                      <tr key={i} className="border-b border-gray-50 dark:border-gray-800/50">
                        <td className="py-2 pr-3 text-gray-700 dark:text-gray-300">{k.keyword}</td>
                        <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{k.position ?? "—"}</td>
                        <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{k.search_volume ?? "—"}</td>
                        <td className="py-2 pr-3 text-gray-500 dark:text-gray-400">{k.cpc != null ? `$${k.cpc}` : "—"}</td>
                        <td className="max-w-xs truncate py-2 text-gray-500 dark:text-gray-400" title={k.url}>
                          <a href={k.url} target="_blank" rel="noreferrer" className="text-brand-600 hover:underline dark:text-brand-400">
                            {k.url}
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
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
      <KeywordResearchCard />
      <KeywordDifficultyCard />
      <RapidApiKeywordCard siteId={siteId} />
      <TopBacklinksCard siteId={siteId} siteUrl={siteUrl} />
      <DomainAuthorityCard siteId={siteId} siteUrl={siteUrl} />
      <KeywordInsightsCard />
      <WebsiteTrafficCard siteId={siteId} siteUrl={siteUrl} />
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
  // Set from anywhere (e.g. PageSpeed's fix list) that resolves an edit
  // target to a static file with no CMS post behind it — switches to the
  // Overview tab, where the Server Files browser lives, and jumps it
  // straight to that file.
  const [serverJumpPath, setServerJumpPath] = useState<string | null>(null);
  const toast = useToast();

  const openStaticFileForEdit = (path: string) => {
    setServerJumpPath(path);
    setTab("overview");
    toast.success(`Opening ${path} in Server Files.`);
  };

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

              {tab === "overview" && (
                <OverviewTab
                  site={selectedSite}
                  serverJumpPath={serverJumpPath}
                  onServerJumpHandled={() => setServerJumpPath(null)}
                  onEditStaticFile={openStaticFileForEdit}
                />
              )}
              {tab === "performance" && (
                <PerformanceTab
                  siteId={selectedSite.id}
                  siteUrl={selectedSite.base_url}
                  onEditStaticFile={openStaticFileForEdit}
                />
              )}
              {tab === "search-console" && <SearchConsoleTab siteId={selectedSite.id} />}
              {tab === "analytics" && <Ga4Tab siteId={selectedSite.id} />}
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
