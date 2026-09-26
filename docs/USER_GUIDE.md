# WorkPulse AI — User Guide

How to use the WorkPulse AI dashboard day to day. No technical knowledge is needed except where a section says
it is for an administrator.

## Contents

1. [What WorkPulse AI does](#1-what-workpulse-ai-does)
2. [Getting started](#2-getting-started)
3. [Finding your way around](#3-finding-your-way-around)
4. [Dashboard](#4-dashboard)
5. [Timeline](#5-timeline)
6. [Attendance](#6-attendance)
7. [Reports (Daily Activity Reports)](#7-reports-daily-activity-reports)
8. [Analytics](#8-analytics)
9. [Alerts and Settings](#9-alerts-and-settings)
10. [Command Mode](#10-command-mode)
11. [LinkedIn](#11-linkedin)
12. [Email](#12-email)
13. [Team (managers and admins)](#13-team-managers-and-admins)
14. [Notepad](#14-notepad)
15. [SEO](#15-seo)
16. [The desktop agent](#16-the-desktop-agent)
17. [Frequently asked questions](#17-frequently-asked-questions)
18. [Glossary](#18-glossary)

---

## 1. What WorkPulse AI does

WorkPulse AI has three parts:

- **Work tracking.** A small program on your PC (the *desktop agent*) notes which apps and websites you use and
  when you are idle. WorkPulse turns that into a focus score, a timeline, attendance and an AI-written daily report.
- **SEO tools.** For each website you manage, WorkPulse audits it, reads Google Search Console and Analytics,
  writes and publishes blog and social posts, and builds the sitemap.
- **Automation.** LinkedIn posts, email campaigns and a command box that runs a plain-language instruction.

All AI runs on your own computer. Your activity data is not sent to a cloud AI service.

---

## 2. Getting started

### Signing in

1. Open the dashboard address you were given (on a local install: `http://localhost:5173`).
2. Enter your email and password and choose **Sign in**. If your organisation has enabled it, **Sign in with
   Google** also appears — it only works for accounts an administrator has already created.

On a brand-new installation the page says **Create the Admin Account**. The first account created becomes the
administrator.

### Roles

| Role | What you see |
|---|---|
| **Employee** | Your own activity, attendance, reports and alerts, plus the SEO, Command Mode, LinkedIn, Email and Notepad pages |
| **Manager** | Everything an employee sees, plus the **Team** page (read-only view of every employee, and AI team analysis) |
| **Admin** | Everything a manager sees, plus creating and removing users, changing roles and resetting passwords |

You can change your own password under **Settings**. If a page says *Access restricted*, your role does not include
it — ask an administrator.

### If your dashboard looks empty

Tracked pages (Dashboard, Timeline, Analytics, Attendance) show data only when the desktop agent is running on your
PC under your account. See [The desktop agent](#16-the-desktop-agent).

---

## 3. Finding your way around

- **Left sidebar:** Dashboard, Timeline, Attendance, Reports, Analytics, Command Mode, LinkedIn, Email, Team
  (managers and admins), SEO, Notepad, Settings. Use the menu button at the top left to collapse it.
- **Top bar:** the day and a status line, the **light / dark theme** switch, the **notification bell** (unread
  alerts) and your account menu.
- **Notifications:** pop-up messages appear at the top centre. Green means done; red means something failed and
  states why. Errors stay on screen longer than confirmations.
- **Pages keep their place.** Switching pages does not cancel work in progress — a running SEO audit, for example,
  is still running when you come back.

---

## 4. Dashboard

Your day at a glance: your **focus score** and **today's metrics** (such as active hours), updated through the day as
the agent records activity. **Quick Actions** jump to common tasks: **Generate DAR Now**, **View Today's Timeline**,
**Post to LinkedIn** and **Run Email Campaign**.

---

## 5. Timeline

A minute-by-minute view of your work day: which apps and sites you used, idle periods and breaks. Use the date
selector to review a past day.

---

## 6. Attendance

Attendance is worked out **automatically** from tracked activity — nothing to fill in.

- **Check-in** is recorded the first time a configured check-in app (by default Zoho) is in the foreground.
- **Sundays and the 1st and 3rd Saturday** of each month are paid week-offs.
- On other days, active time is classified as a **full day**, **half day** or **absent**, based on how much of the
  work shift you were active.
- A check-in outside the sanctioned punch-in windows counts as **late**. Reaching the monthly late limit
  (three, by default) raises a warning alert and an email.
- The **Weekly Consistency** chart shows how steady your week was.

These rules and times are set by your organisation's configuration; ask your administrator if yours differ.

---

## 7. Reports (Daily Activity Reports)

The **Reports** page holds your AI-written **Daily Activity Report (DAR)** and **weekly reports**.

- Each day's report is generated automatically in the evening. Press **Generate Now** to create today's on demand.
- Reports have a **narrative** view (a written summary) and a **structured task log**.
- **Departments** can have their own report template with custom fields; the report follows your department's template.
- **Export** a report as CSV, DOCX or PDF, and **import** task entries from CSV.
- **Email** (or **Resend**) sends the report to the configured address.

Review the AI's wording before sending — it is a draft of what you did, based on tracked activity.

---

## 8. Analytics

Charts for the selected day and for the last several days:

- **Top apps** and **category split** (productive, neutral, distracting).
- **Focus score** for the day and the period average.
- **Peak hours heatmap** — when you are most active over the last seven days.
- **Context switching** — how often you jump between apps, and when it becomes excessive.

---

## 9. Alerts and Settings

WorkPulse raises smart alerts and shows them under the **bell** in the top bar:

| Alert | Trigger |
|---|---|
| Focus | A long idle stretch during work hours |
| Distraction | Too large a share of an hour spent on distracting apps or sites |
| Wellbeing | A very long day, or several long days in a row (burnout risk) |
| Manager alert | A team member with no activity for a long time (managers) |

Click an alert to read it and dismiss it when done. Under **Settings → Alert Preferences**, switch each alert type
on or off.

---

## 10. Command Mode

Type an instruction in plain language and the Master Agent carries it out — for example *"generate today's report"*
or *"post to LinkedIn about agentic AI"*.

1. Type the instruction and press **Run**.
2. Watch the live log and progress bar. You can **Cancel** a running command.
3. **Job History** lists earlier commands and their results.

SEO audit commands (such as *"audit the site"*) are available to managers and admins.

---

## 11. LinkedIn

Generate and post LinkedIn content automatically. Enter an optional **topic** (or leave it blank for the AI to
choose), start the run, and follow the status. **Posts Today**, **Last Post** and **Post History** show what has
gone out. Posting uses a saved LinkedIn session, so an administrator must have signed the account in once.

---

## 12. Email

Personalised outreach campaigns sent through Gmail.

- **Sent Today / Total Sent / Total Failed** summarise activity.
- **Campaign Log** lists each send with the lead, subject, status and follow-up.
- **Leads** are the people being contacted; **Mail Templates** are reusable message templates.

Email needs Gmail credentials configured by an administrator.

---

## 13. Team (managers and admins)

An overview of every team member: status (active / idle / offline), focus score, hours worked and current app.

- Open a member to see their **timeline**, **attendance calendar** and **report history**.
- **AI team analysis** (weekly) highlights high performers, people who may be struggling, workload imbalance and
  burnout risk.
- The comparison chart has an **anonymise** option for sensitive settings.
- **Admins** can add members, change roles, reset passwords, and turn features on or off per employee (activity
  tracking, report generation, alerts). Those switches control the employee's own desktop agent, not just what
  the dashboard shows.

---

## 14. Notepad

A simple notepad for notes, snippets and ideas. Choose **New note**, give it a title and write. Notes are saved to
your account.

---

## 15. SEO

The **SEO** page manages the websites you look after. Everything on it applies to the **site chosen in the
selector at the top**, and your choice is remembered.

> **Tip:** each tab has its own link. **Ctrl+click** (or middle-click) a tab to open it in a new browser tab.

### 15.1 Add a site and connect it

1. Select **Add site**, enter a name and the site's public address, and choose its CMS (WordPress or Webflow).
2. Open **Overview** and connect what you need. Each card shows **Saved** once stored; press **Change** to edit
   and **Save** (or **Cancel**).

| Card | What to enter | Needed for |
|---|---|---|
| **Google Search Console & Analytics** | The Search Console property address and the GA4 property id | Search Console, Analytics, Indexing, sitemap submission |
| **CMS Publishing** | For WordPress: site address, username and an **Application Password**. For Webflow: API token and collection id | Publishing blog posts, applying fixes |
| **Server Access** | SFTP or FTP host, port, username, password | Editing site files, uploading images, redirects, sitemap upload |
| **Google Sheets cards** | A blank Google Sheet you have shared with the service account as *Editor*, then paste its link | Exporting posts, calendars and pipeline logs |

**Application Password (WordPress):** in WordPress go to *Users → Profile → Application Passwords*, create one, and
paste it here. Your normal login password will not work for publishing.

**Search Console access:** an administrator must add WorkPulse's Google service account to your property in Google
Search Console — *Restricted* is enough for reports; **Full** is needed for URL Inspection and sitemap
submission.

### 15.2 Overview

Site health and the daily routine in one place:

- **Digest and roll-ups.** WorkPulse writes a daily summary automatically. **Weekly / monthly roll-up** produces a
  longer report for a week, month or custom period; choose which metrics to include, then **Generate now**. It
  takes a minute or two and keeps running if you switch tabs. If the AI is unavailable it says so and a retry
  works.
- **Job history** shows what the daily automation did and any failures.
- **Search insight cards** — **Top Search Queries**, **Top Traffic Pages**, **CTR by Page**, **Rank Alerts** (sudden
  ranking drops) and **Meta Rewrite Opportunities** (pages whose title or description could earn more clicks).
- **Server Files** — browse and edit files on the site's server, with a history you can restore from (kept 15 days).
- **Convert page images to WebP** — shrink a page's images.

### 15.3 Technical Audit

Finds technical SEO problems on the site.

1. Press **Run Technical Audit**. A large site takes a few minutes; a progress bar shows it working.
2. Review **Technical Issues**. Filter by **Pending, Approved, Rejected, Resolved** or **All**.
3. For each issue you can **Approve**, **Reject**, **Get AI suggestion**, **Generate fix** (a ready-to-use replacement),
   **Edit this page**, or **Mark as fixed manually**. Applying a fix changes the live site, so it always needs your
   approval first.
4. **Run Technical Audit — Individual Page** checks one page's tags (title, description, canonical, Open Graph,
   structured data, H1) without crawling the whole site.

The audit also runs automatically every day.

### 15.4 Performance

Runs Google PageSpeed for the site: Core Web Vitals, page weight, unused CSS/JS and a prioritised list of fixes.
Enter a page address and press **Run Page Speed Check**; earlier results are listed below.

### 15.5 Search Console

- **Search Console Performance** — clicks, impressions, click-through rate and average position over 24 hours, 7
  or 28 days, 3 months or a custom range. Toggle the metrics on the chart. **Search** across queries, pages and
  countries, set minimums, or use **Top 10 rankings**, then open the tables for Queries, Pages, Countries,
  Devices and Search appearance.
- **Sitemap Generator** — see below.
- **Sitemaps** — submit a sitemap to Google and see what Google has processed. The address defaults to your
  site's `sitemap.xml`.

#### Sitemap Generator

Builds the site's `sitemap.xml` for you — no 500-page limit and no hand-typing thousands of URLs.

1. Press **Generate sitemap**. WorkPulse reads the CMS content, any existing sitemap and the live site, and
   checks each page is reachable and indexable. Progress is shown; you can leave the page.
2. The result is **one `sitemap.xml`** with your **home page, service pages, blog page and posts, categories and
   tags**, in that priority order, and each page's **images and videos** listed with it. (A very large site over
   Google's 50,000-URL limit is split automatically.) Counts and file sizes are shown.
3. If the site has **Server Access** saved, it is uploaded to the site and checked live, then submitted to Google.
   Otherwise use **Download all (.zip)** (or a single file) and upload it to the site's main folder yourself.
   **Upload to server & submit to Google** repeats the upload at any time.
4. Leave **Keep it updated automatically** ticked: the sitemap refreshes about once a day (new and changed pages are
   picked up) and a blog post is added within seconds of going live.

The card may note that the site's `robots.txt` should contain a `Sitemap:` line; add it if so.

### 15.6 Analytics

Google Analytics (GA4): a **realtime overview**, **performance** (users, sessions, engagement by page, source,
country, device) and **events**.

### 15.7 Indexing

**Index coverage** shows whether Google has indexed your pages. Enter a page address and press **Inspect** for
details — whether it is indexed, when it was last crawled, and which canonical Google chose. If Inspect reports a
permission problem, the message names the Google account to add to Search Console and the access level needed.

### 15.8 Social

Create, review and publish posts for LinkedIn, X (Twitter), Instagram and Facebook.

- **Generate social content** — enter a page title and excerpt, choose platforms, and the AI drafts a post for each.
  You can also **bulk-generate** from several topics or create a **30-day content calendar**.
- **Posts** lists every post. Use **Add post** to write one yourself.
- On any post that is not yet published you can **Edit** (text, platform, source link, image link), **Delete**,
  **Generate image** (AI) or **Upload image**, **Approve** or **Reject**, **Schedule** a date and time, and
  **Publish**. A counter shows the platform's character limit; you cannot save a post that is too long.
- Instagram posts need an image before they can be published.
- Select several posts to **Bulk approve**, **Bulk publish** or **Bulk delete**.
- **Export to Sheet** writes every post to your connected Google Sheet.

Approval is a deliberate step: nothing is published until you approve it (scheduled posts go out at their time).

### 15.9 Blog

**Generate a blog post** — enter a topic and keyword. WorkPulse writes the article first (about 700–800 words, usually
a few minutes) and shows the draft as soon as it is ready. The meta title and description, keyword density, five FAQs,
internal links and the plagiarism and grammar checks are then prepared in the background — a banner on the post shows
what it is working on, and you can read and edit meanwhile.

Each draft shows badges for **structure issues** (missing H1, too short), **plagiarism**, **AI-content score** and
**grammar**. Use **Re-check** after editing.

A draft moves through: **Draft → Approved → Published (as a CMS draft) → Live.**

- **Preview** shows how it will look; **View content** expands the text.
- **Edit** opens the editor: headings, bold, lists, links, tables, images and more. The **copy** button at the right
  of the toolbar copies the whole article (formatting included) to paste elsewhere.
- **SEO Tools** — meta title/description, slug, tags, categories, keyword density, internal links, image.
- **Approve**, then **Publish**. Publishing creates a **draft in your CMS** — it does not make the page public. It
  adds a featured image (generated if none) **centred after the first paragraph**, and related-reading links.
- Press **Go Live** when you are ready for it to become public.
- **Schedule** a date and time to publish automatically.
- **Content calendar** plans a series of posts; **Export to Sheet** sends them to Google Sheets.

Publishing can take a minute or more because it generates and uploads an image first — wait for the message rather
than clicking again. If it fails, the post shows the reason and can be retried.

### 15.10 Backlinks

**Brand mentions** tracks new web mentions of your brand and can draft an outreach email (you send it). Research
cards cover keyword research and difficulty, backlinks, domain authority and competitor analysis. Some of these
need an API key from your administrator and are hidden until it is set up.

### 15.11 Redirection

Manage URL redirects (**Permanent Redirect (301)** or **Temporary Redirect (302)**). **Add a redirect**, or edit or remove one from **All
redirects**. Redirects are written to the site's `.htaccess` when Server Access is connected, and their sync status
is shown.

### 15.12 Common tasks

**Publish a blog post**
1. **Blog → Generate a blog post** → fix any structure or grammar issues → **Approve** → **Publish** → check it in
   your CMS → **Go Live**.

**Get every page into Google**
1. **Search Console → Sitemap Generator → Generate sitemap.** 2. Confirm it shows *Live on the site*. 3. Check that
   **Sitemaps** lists it as submitted.

**Fix a technical problem**
1. **Technical Audit → Run Technical Audit.** 2. Open a pending issue → **Get AI suggestion** or **Generate fix**.
   3. **Approve** and apply it, or **Edit this page** to change it by hand. 4. Re-run the audit to confirm.

**Post a week of social content**
1. **Social → Generate a content calendar** (or Add post). 2. Add images. 3. Approve. 4. Schedule or Publish.

---

## 16. The desktop agent

The agent is a small program that runs in the system tray and records what you use so the dashboard has data.

- **Install:** run `WorkPulseAgent.exe`. On first launch a setup window asks for the **server address** and your
  **user id**. It then starts with Windows.
- **What it records:** the foreground application, the website (from the window title), idle time and breaks,
  meetings from a calendar file, and — only if your organisation enables it — activity in shared folders.
- **What it does not record:** it does not take screenshots, log keystrokes or read the content of your windows.
- **Idle time:** after five minutes without keyboard or mouse activity you are marked idle (WorkPulse only measures
  *that* input occurred, not what was typed); a meeting on your calendar is not counted as idle.
- **Status:** the tray icon shows it is running; the dashboard shows you as active, idle or offline.

If the dashboard is empty, check that the agent is running and that its user id matches your login.

---

## 17. Frequently asked questions

**The dashboard shows no data for me.** The agent must be running under your account. Restart it and check the tray
icon; then wait a minute for the first data.

**"GSC fetch failed" on an SEO tab.** Google has not given WorkPulse access to that site. Ask an administrator to
add the service account as a user in Search Console and to enable the API.

**Publishing a blog post says it failed but it is in WordPress.** Publishing runs long; refresh the Blog tab and
check the post's status before retrying.

**Publishing says 401 Unauthorized.** The WordPress username or Application Password is wrong. Create a new
Application Password and re-enter it in **CMS Publishing**.

**Why is the AI slow?** The AI runs on your computer. A long article or roll-up can take a few minutes; a progress
bar shows it is working.

**Where does my data go?** It stays in the WorkPulse database on your organisation's server. AI processing is local.
Optional integrations (Google, your CMS, Gmail, social networks) only send what those features need.

**Can I open a tab in a new browser tab?** On the SEO page, yes — Ctrl+click or middle-click a tab.

**A card I expect is missing (for example Semrush).** Some cards stay hidden until their service is set up. Ask an
administrator.

---

## 18. Glossary

| Term | Meaning |
|---|---|
| **DAR** | Daily Activity Report — the AI-written summary of your day |
| **Focus score** | A 0–100 measure of how much of your active time was productive |
| **Agent** | The desktop program that records activity |
| **GSC** | Google Search Console |
| **GA4** | Google Analytics 4 |
| **CMS** | The system your website runs on (WordPress, Webflow) |
| **Application Password** | A special WordPress password for apps such as WorkPulse |
| **Sitemap** | A file listing a site's pages, images and videos so search engines find them |
| **Canonical** | The preferred address of a page when several addresses show the same content |
| **Indexed** | Stored in Google's search index and eligible to appear in results |
| **Core Web Vitals** | Google's page-speed and stability measurements |
| **Go Live** | Changing a CMS draft to public |
| **SFTP / FTP** | Ways to transfer files to a website's server |

---

*Last updated: September 25, 2026.*
