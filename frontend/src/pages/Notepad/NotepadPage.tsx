import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useEditor, EditorContent, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import TextAlign from "@tiptap/extension-text-align";
import {
  AlignCenter,
  AlignLeft,
  AlignRight,
  Bold,
  Check,
  Code,
  Code2,
  Copy,
  Download,
  Eye,
  EyeOff,
  Heading1,
  Heading2,
  Heading3,
  Italic,
  Link as LinkIcon,
  List,
  ListOrdered,
  Minus,
  Pin,
  PinOff,
  Plus,
  Quote,
  Redo2,
  Search,
  Strikethrough,
  Trash2,
  Undo2,
  X,
} from "lucide-react";

import PageMeta from "@/components/common/PageMeta";
import { useAuth } from "@/context/AuthContext";
import { deleteNoteApi, getNotes, saveNote, type NoteColor } from "@/api";

type Note = {
  id: string;
  title: string;
  html: string;
  tags: string[];
  color: NoteColor;
  pinned: boolean;
  createdAt: number;
  updatedAt: number;
};

const COLORS: Record<NoteColor, { dot: string; bar: string }> = {
  gray: { dot: "bg-gray-400", bar: "border-l-gray-400" },
  blue: { dot: "bg-blue-500", bar: "border-l-blue-500" },
  green: { dot: "bg-emerald-500", bar: "border-l-emerald-500" },
  amber: { dot: "bg-amber-500", bar: "border-l-amber-500" },
  rose: { dot: "bg-rose-500", bar: "border-l-rose-500" },
  purple: { dot: "bg-purple-500", bar: "border-l-purple-500" },
};

const newNote = (): Note => {
  const now = Date.now();
  return {
    id: `${now.toString(36)}${Math.random().toString(36).slice(2, 7)}`,
    title: "",
    html: "",
    tags: [],
    color: "gray",
    pinned: false,
    createdAt: now,
    updatedAt: now,
  };
};

const htmlToText = (html: string): string => {
  const el = document.createElement("div");
  el.innerHTML = html;
  return (el.innerText || el.textContent || "").replace(/ /g, " ");
};

const wordCount = (text: string): number => (text.trim() ? text.trim().split(/\s+/).length : 0);

const formatWhen = (ts: number): string => {
  const d = new Date(ts);
  const sameDay = d.toDateString() === new Date().toDateString();
  return sameDay
    ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" });
};

const download = (filename: string, content: string, type: string) => {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

function ToolbarButton({
  label,
  active,
  disabled,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      disabled={disabled}
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      className={`flex h-8 w-8 items-center justify-center rounded-md text-gray-600 transition-colors disabled:opacity-30 dark:text-gray-300 ${
        active
          ? "bg-brand-500/15 text-brand-600 dark:text-brand-400"
          : "hover:bg-gray-100 dark:hover:bg-white/10"
      }`}
    >
      {children}
    </button>
  );
}

const Divider = () => <span className="mx-1 h-5 w-px bg-gray-200 dark:bg-gray-700" />;

function Toolbar({ editor }: { editor: Editor }) {
  const setLink = () => {
    const prev = editor.getAttributes("link").href as string | undefined;
    const url = window.prompt("Link URL (leave empty to remove)", prev ?? "https://");
    if (url === null) return;
    if (url.trim() === "") {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange("link").setLink({ href: url.trim() }).run();
  };
  const c = () => editor.chain().focus();
  return (
    <div className="flex flex-wrap items-center gap-0.5 border-b border-gray-200 px-2 py-1.5 dark:border-gray-800">
      <ToolbarButton label="Undo" disabled={!editor.can().undo()} onClick={() => c().undo().run()}>
        <Undo2 className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Redo" disabled={!editor.can().redo()} onClick={() => c().redo().run()}>
        <Redo2 className="h-4 w-4" />
      </ToolbarButton>
      <Divider />
      <ToolbarButton label="Heading 1" active={editor.isActive("heading", { level: 1 })} onClick={() => c().toggleHeading({ level: 1 }).run()}>
        <Heading1 className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Heading 2" active={editor.isActive("heading", { level: 2 })} onClick={() => c().toggleHeading({ level: 2 }).run()}>
        <Heading2 className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Heading 3" active={editor.isActive("heading", { level: 3 })} onClick={() => c().toggleHeading({ level: 3 }).run()}>
        <Heading3 className="h-4 w-4" />
      </ToolbarButton>
      <Divider />
      <ToolbarButton label="Bold" active={editor.isActive("bold")} onClick={() => c().toggleBold().run()}>
        <Bold className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Italic" active={editor.isActive("italic")} onClick={() => c().toggleItalic().run()}>
        <Italic className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Strikethrough" active={editor.isActive("strike")} onClick={() => c().toggleStrike().run()}>
        <Strikethrough className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Inline code" active={editor.isActive("code")} onClick={() => c().toggleCode().run()}>
        <Code className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Link" active={editor.isActive("link")} onClick={setLink}>
        <LinkIcon className="h-4 w-4" />
      </ToolbarButton>
      <Divider />
      <ToolbarButton label="Bullet list" active={editor.isActive("bulletList")} onClick={() => c().toggleBulletList().run()}>
        <List className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Numbered list" active={editor.isActive("orderedList")} onClick={() => c().toggleOrderedList().run()}>
        <ListOrdered className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Quote" active={editor.isActive("blockquote")} onClick={() => c().toggleBlockquote().run()}>
        <Quote className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Code block" active={editor.isActive("codeBlock")} onClick={() => c().toggleCodeBlock().run()}>
        <Code2 className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Divider line" onClick={() => c().setHorizontalRule().run()}>
        <Minus className="h-4 w-4" />
      </ToolbarButton>
      <Divider />
      <ToolbarButton label="Align left" active={editor.isActive({ textAlign: "left" })} onClick={() => c().setTextAlign("left").run()}>
        <AlignLeft className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Align center" active={editor.isActive({ textAlign: "center" })} onClick={() => c().setTextAlign("center").run()}>
        <AlignCenter className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label="Align right" active={editor.isActive({ textAlign: "right" })} onClick={() => c().setTextAlign("right").run()}>
        <AlignRight className="h-4 w-4" />
      </ToolbarButton>
    </div>
  );
}

// Styling for the editor content (the project has no typography plugin).
const CONTENT_CLASS =
  "min-h-full px-5 py-4 text-sm leading-relaxed text-gray-800 outline-none dark:text-gray-200 " +
  "[&_h1]:mb-2 [&_h1]:mt-4 [&_h1]:text-2xl [&_h1]:font-bold " +
  "[&_h2]:mb-2 [&_h2]:mt-3 [&_h2]:text-xl [&_h2]:font-semibold " +
  "[&_h3]:mb-1.5 [&_h3]:mt-3 [&_h3]:text-lg [&_h3]:font-semibold " +
  "[&_p]:my-1.5 [&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-6 " +
  "[&_blockquote]:my-2 [&_blockquote]:border-l-4 [&_blockquote]:border-gray-300 [&_blockquote]:pl-3 [&_blockquote]:italic [&_blockquote]:text-gray-600 dark:[&_blockquote]:border-gray-600 dark:[&_blockquote]:text-gray-400 " +
  "[&_code]:rounded [&_code]:bg-gray-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[13px] dark:[&_code]:bg-white/10 " +
  "[&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-gray-900 [&_pre]:p-3 [&_pre]:text-gray-100 [&_pre_code]:bg-transparent [&_pre_code]:p-0 " +
  "[&_a]:text-brand-500 [&_a]:underline [&_hr]:my-4 [&_hr]:border-gray-200 dark:[&_hr]:border-gray-700 " +
  "[&_.is-editor-empty:first-child::before]:pointer-events-none [&_.is-editor-empty:first-child::before]:float-left [&_.is-editor-empty:first-child::before]:h-0 [&_.is-editor-empty:first-child::before]:text-gray-400 [&_.is-editor-empty:first-child::before]:content-[attr(data-placeholder)]";

function NoteEditor({
  note,
  onChange,
  onDelete,
  syncLabel,
}: {
  note: Note;
  onChange: (patch: Partial<Note>) => void;
  onDelete: () => void;
  syncLabel: string;
}) {
  const [tagInput, setTagInput] = useState("");
  const [copied, setCopied] = useState(false);
  const [preview, setPreview] = useState(false);
  const [stats, setStats] = useState({ words: 0, chars: 0 });
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const editor = useEditor({
    extensions: [
      StarterKit,
      Link.configure({ openOnClick: false, autolink: true }),
      Placeholder.configure({ placeholder: "Start writing… paste anything: meeting notes, snippets, links, ideas." }),
      TextAlign.configure({ types: ["heading", "paragraph"] }),
    ],
    content: note.html,
    editorProps: { attributes: { class: CONTENT_CLASS } },
    onUpdate: ({ editor: ed }) => {
      onChangeRef.current({ html: ed.isEmpty ? "" : ed.getHTML() });
      const text = ed.getText();
      setStats({ words: wordCount(text), chars: text.length });
    },
  });

  // Notes are switched by remounting this component (keyed on note.id), so the
  // initial stats only need computing once per note.
  useEffect(() => {
    if (!editor) return;
    const text = editor.getText();
    setStats({ words: wordCount(text), chars: text.length });
  }, [editor]);

  useEffect(() => {
    editor?.setEditable(!preview);
  }, [editor, preview]);

  const addTag = () => {
    const t = tagInput.trim().replace(/^#/, "");
    if (t && !note.tags.includes(t)) onChange({ tags: [...note.tags, t] });
    setTagInput("");
  };

  const plainText = () => `${note.title ? note.title + "\n\n" : ""}${editor?.getText({ blockSeparator: "\n" }) ?? htmlToText(note.html)}`;
  const safeName = (note.title || "note").replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "-") || "note";

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(plainText());
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <div className="flex h-[calc(100vh-11rem)] min-h-[480px] flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 px-4 py-3 dark:border-gray-800">
        <input
          value={note.title}
          onChange={(e) => onChange({ title: e.target.value })}
          placeholder="Untitled note"
          className="min-w-0 flex-1 bg-transparent text-lg font-semibold text-gray-900 outline-none placeholder:text-gray-400 dark:text-white"
        />
        <div className="flex items-center gap-1">
          {(Object.keys(COLORS) as NoteColor[]).map((c) => (
            <button
              key={c}
              type="button"
              title={`Label: ${c}`}
              aria-label={`Label ${c}`}
              onClick={() => onChange({ color: c })}
              className={`h-4 w-4 rounded-full ${COLORS[c].dot} ${note.color === c ? "ring-2 ring-offset-2 ring-gray-400 dark:ring-offset-gray-900" : "opacity-60 hover:opacity-100"}`}
            />
          ))}
        </div>
        <Divider />
        <ToolbarButton label={note.pinned ? "Unpin" : "Pin to top"} active={note.pinned} onClick={() => onChange({ pinned: !note.pinned })}>
          {note.pinned ? <PinOff className="h-4 w-4" /> : <Pin className="h-4 w-4" />}
        </ToolbarButton>
        <ToolbarButton label={preview ? "Back to editing" : "Read-only view"} active={preview} onClick={() => setPreview((p) => !p)}>
          {preview ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </ToolbarButton>
        <ToolbarButton label={copied ? "Copied" : "Copy as text"} onClick={copy}>
          {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
        </ToolbarButton>
        <ToolbarButton label="Download .txt" onClick={() => download(`${safeName}.txt`, plainText(), "text/plain")}>
          <Download className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          label="Download .html"
          onClick={() =>
            download(
              `${safeName}.html`,
              `<!doctype html><meta charset="utf-8"><title>${note.title || "Note"}</title><h1>${note.title}</h1>${note.html}`,
              "text/html",
            )
          }
        >
          <span className="text-[10px] font-bold">HTML</span>
        </ToolbarButton>
        <ToolbarButton label="Delete note" onClick={onDelete}>
          <Trash2 className="h-4 w-4 text-rose-500" />
        </ToolbarButton>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 border-b border-gray-200 px-4 py-2 dark:border-gray-800">
        {note.tags.map((t) => (
          <span key={t} className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700 dark:bg-white/10 dark:text-gray-300">
            #{t}
            <button type="button" aria-label={`Remove tag ${t}`} onClick={() => onChange({ tags: note.tags.filter((x) => x !== t) })}>
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              addTag();
            }
          }}
          onBlur={addTag}
          placeholder="Add tag…"
          className="w-24 bg-transparent text-xs text-gray-700 outline-none placeholder:text-gray-400 dark:text-gray-300"
        />
      </div>

      {editor && !preview && <Toolbar editor={editor} />}
      <div className="min-h-0 flex-1 overflow-y-auto" onClick={() => editor?.chain().focus().run()}>
        <EditorContent editor={editor} />
      </div>

      <div className="flex items-center justify-between border-t border-gray-200 px-4 py-2 text-xs text-gray-500 dark:border-gray-800 dark:text-gray-400">
        <span>
          {stats.words} words · {stats.chars} characters
        </span>
        <span>
          {syncLabel} · edited {formatWhen(note.updatedAt)}
        </span>
      </div>
    </div>
  );
}

export default function NotepadPage() {
  const { user } = useAuth();
  const storageKey = `workpulse.notepad.v1.${user?.id ?? "guest"}`;

  const [notes, setNotes] = useState<Note[]>(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      const parsed = raw ? (JSON.parse(raw) as Note[]) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });
  const [activeId, setActiveId] = useState<string | null>(() => notes[0]?.id ?? null);
  const [query, setQuery] = useState("");
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [sync, setSync] = useState<"loading" | "saving" | "saved" | "offline">("loading");

  const pendingKey = `${storageKey}.pendingDeletes`;
  // id -> updatedAt last confirmed stored in the database.
  const synced = useRef(new Map<string, number>());
  const notesRef = useRef(notes);
  notesRef.current = notes;

  const readPendingDeletes = useCallback((): string[] => {
    try {
      const v = JSON.parse(localStorage.getItem(pendingKey) ?? "[]");
      return Array.isArray(v) ? v : [];
    } catch {
      return [];
    }
  }, [pendingKey]);

  const writePendingDeletes = useCallback(
    (ids: string[]) => {
      try {
        localStorage.setItem(pendingKey, JSON.stringify(ids));
      } catch {
        /* storage full or blocked */
      }
    },
    [pendingKey],
  );

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(notes));
    } catch {
      /* storage full or blocked */
    }
  }, [notes, storageKey]);

  // Initial load: merge the database copy with this browser's copy. The newer
  // version of each note wins; notes only the browser has get uploaded.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const pending = readPendingDeletes();
        for (const id of pending) await deleteNoteApi(id);
        writePendingDeletes([]);
        const server = (await getNotes()).filter((n) => !pending.includes(n.id));
        if (cancelled) return;
        const merged = new Map<string, Note>(notesRef.current.filter((n) => !pending.includes(n.id)).map((n) => [n.id, n]));
        for (const sn of server) {
          synced.current.set(sn.id, sn.updatedAt);
          const local = merged.get(sn.id);
          if (!local || sn.updatedAt > local.updatedAt) merged.set(sn.id, sn);
        }
        setNotes([...merged.values()].sort((a, b) => b.updatedAt - a.updatedAt));
        setActiveId((cur) => cur ?? [...merged.keys()][0] ?? null);
        setSync("saved");
      } catch {
        if (!cancelled) setSync("offline");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [readPendingDeletes, writePendingDeletes]);

  // Push edited notes to the database shortly after typing stops.
  useEffect(() => {
    if (sync === "loading") return;
    const dirty = notes.filter((n) => (synced.current.get(n.id) ?? -1) < n.updatedAt);
    if (dirty.length === 0) return;
    setSync("saving");
    const timer = setTimeout(async () => {
      try {
        await Promise.all(
          dirty.map(async (n) => {
            await saveNote(n);
            synced.current.set(n.id, n.updatedAt);
          }),
        );
        setSync("saved");
      } catch {
        setSync("offline");
      }
    }, 800);
    return () => clearTimeout(timer);
  }, [notes, sync === "loading"]); // eslint-disable-line react-hooks/exhaustive-deps

  const syncLabel =
    sync === "saved" ? "Saved to database" : sync === "saving" ? "Saving…" : sync === "loading" ? "Loading…" : "Offline — saved in this browser, will retry";

  const update = useCallback((id: string, patch: Partial<Note>) => {
    setNotes((prev) => prev.map((n) => (n.id === id ? { ...n, ...patch, updatedAt: Date.now() } : n)));
  }, []);

  const create = () => {
    const n = newNote();
    setNotes((prev) => [n, ...prev]);
    setActiveId(n.id);
  };

  const remove = (id: string) => {
    if (!window.confirm("Delete this note? This cannot be undone.")) return;
    synced.current.delete(id);
    deleteNoteApi(id).catch(() => writePendingDeletes([...readPendingDeletes(), id]));
    const rest = notes.filter((n) => n.id !== id);
    setNotes(rest);
    setActiveId(rest[0]?.id ?? null);
  };

  const allTags = useMemo(() => [...new Set(notes.flatMap((n) => n.tags))].sort(), [notes]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return notes
      .filter((n) => (tagFilter ? n.tags.includes(tagFilter) : true))
      .filter((n) => !q || n.title.toLowerCase().includes(q) || htmlToText(n.html).toLowerCase().includes(q) || n.tags.some((t) => t.toLowerCase().includes(q)))
      .sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.updatedAt - a.updatedAt);
  }, [notes, query, tagFilter]);

  const active = notes.find((n) => n.id === activeId) ?? null;

  return (
    <>
      <PageMeta title="Notepad | WorkPulse AI" description="Advanced notepad for notes, snippets and ideas." />
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Notepad</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Rich notes with tags, colour labels, search and export. Saved to your account and cached in this browser.
          </p>
        </div>
        <button
          type="button"
          onClick={create}
          className="inline-flex items-center gap-1.5 rounded-lg bg-brand-500 px-3.5 py-2 text-sm font-medium text-white hover:bg-brand-600"
        >
          <Plus className="h-4 w-4" /> New note
        </button>
      </div>

      <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
        <div className="flex flex-col gap-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search notes…"
              className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm text-gray-800 outline-none focus:border-brand-500 dark:border-gray-800 dark:bg-white/[0.03] dark:text-gray-200"
            />
          </div>
          {allTags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {allTags.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTagFilter(tagFilter === t ? null : t)}
                  className={`rounded-full px-2.5 py-0.5 text-xs ${
                    tagFilter === t ? "bg-brand-500 text-white" : "bg-gray-100 text-gray-700 dark:bg-white/10 dark:text-gray-300"
                  }`}
                >
                  #{t}
                </button>
              ))}
            </div>
          )}
          <div className="flex max-h-[calc(100vh-13rem)] flex-col gap-2 overflow-y-auto pr-1">
            {visible.length === 0 && (
              <p className="rounded-xl border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                {notes.length === 0 ? "No notes yet. Create your first one." : "No notes match your search."}
              </p>
            )}
            {visible.map((n) => (
              <button
                key={n.id}
                type="button"
                onClick={() => setActiveId(n.id)}
                className={`rounded-xl border border-l-4 p-3 text-left transition-colors ${COLORS[n.color].bar} ${
                  n.id === activeId
                    ? "border-brand-500/50 bg-brand-500/5"
                    : "border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-800 dark:bg-white/[0.03] dark:hover:bg-white/[0.06]"
                }`}
              >
                <div className="flex items-center gap-1.5">
                  {n.pinned && <Pin className="h-3 w-3 shrink-0 text-brand-500" />}
                  <span className="truncate text-sm font-medium text-gray-900 dark:text-white">{n.title || "Untitled note"}</span>
                </div>
                <p className="mt-0.5 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">
                  {htmlToText(n.html).slice(0, 160) || "Empty note"}
                </p>
                <p className="mt-1.5 text-[11px] text-gray-400">{formatWhen(n.updatedAt)}</p>
              </button>
            ))}
          </div>
        </div>

        <div>
          {active ? (
            <NoteEditor key={active.id} note={active} onChange={(p) => update(active.id, p)} onDelete={() => remove(active.id)} syncLabel={syncLabel} />
          ) : (
            <div className="rounded-2xl border border-dashed border-gray-300 p-16 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
              Select a note, or create a new one to start writing.
            </div>
          )}
        </div>
      </div>
    </>
  );
}
