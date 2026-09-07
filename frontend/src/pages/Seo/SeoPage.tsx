import { FormEvent, ReactElement, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  Gauge,
  Globe,
  History,
  LayoutDashboard,
  Link2,
  Loader2,
  Mail,
  Plus,
  RefreshCw,
  Search,
  Send,
  Share2,
  Sparkles,
  TrendingUp,
  XCircle,
} from "lucide-react";
import type { AxiosError } from "axios";
import DOMPurify from "dompurify";

import PageMeta from "@/components/common/PageMeta";
import { Button } from "@/components/shadcn/button";
import { Card, CardContent } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import StatCard from "@/components/dashboard/StatCard";
import StatusChip from "@/components/dashboard/StatusChip";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import { useToast } from "@/context/ToastContext";
import {
  approveBlogPost,
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
  getBacklinks,
  getBlogPosts,
  getGa4Pages,
  getGscQueries,
  getIndexingSubmissions,
  getIndexStatusList,
  getPageSpeedOpportunities,
  getPageSpeedResults,
  getSeoDigests,
  getSeoJobs,
  getSeoSites,
  getSocialPosts,
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
  rejectSocialPost,
  rejectTechnicalIssue,
  runTechnicalAudit,
  SeoJobRun,
  SeoSite,
  SocialPlatform,
  StructureIssue,
  submitForIndexing,
  TechnicalIssue,
  updateSeoSiteCmsConfig,
  updateSeoSiteGoogleConfig,
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
    </>
  );
}

function JobHistoryPanel({ jobs, loading }: { jobs: SeoJobRun[]; loading: boolean }) {
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
                  <th className="pb-2 font-medium">Finished</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className="border-b border-gray-50 last:border-0 dark:border-gray-800/50">
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
                    <td className="py-2 text-theme-xs text-gray-400" title={job.error ?? undefined}>
                      {job.finished_at ? job.finished_at.replace("T", " ").slice(0, 19) : "—"}
                      {job.error && <span className="ml-1 text-error-500">({job.error.slice(0, 40)})</span>}
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
  const [selectedPlatforms, setSelectedPlatforms] = useState<SocialPlatform[]>(["linkedin"]);

  const postsQuery = useQuery({ queryKey: ["seo", "social", siteId], queryFn: () => getSocialPosts(siteId) });
  const posts = postsQuery.data ?? [];

  const generateMutation = useMutation({
    mutationFn: () =>
      generateSocialPosts({
        site_id: siteId,
        page_title: pageTitle,
        content_excerpt: contentExcerpt,
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
                  <p className="whitespace-pre-line text-theme-sm text-gray-700 dark:text-gray-300">{post.content}</p>
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
                  {post.status === "approved" && (
                    <Button size="sm" className="mt-3" onClick={() => publishMutation.mutate(post.id)}>
                      <Send className="h-3.5 w-3.5" />
                      Publish
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

  const postsQuery = useQuery({ queryKey: ["seo", "blog", siteId], queryFn: () => getBlogPosts(siteId) });
  const posts = postsQuery.data ?? [];

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
                    {expandedId === post.id && (
                      <div
                        className="prose prose-sm mt-3 max-w-none rounded-md bg-gray-50 p-4 dark:bg-white/5 dark:prose-invert"
                        dangerouslySetInnerHTML={{ __html: sanitizeBlogHtml(post.content) }}
                      />
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
