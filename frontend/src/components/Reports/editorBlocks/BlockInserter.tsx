import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Editor } from "@tiptap/react";
import {
  Bookmark,
  Heading1,
  Heading2,
  Heading3,
  Image as ImageIcon,
  List,
  ListOrdered,
  Minus,
  Pilcrow,
  Plus,
  Quote,
  Search,
  X,
} from "lucide-react";

interface BlockDef {
  id: string;
  label: string;
  icon: ReactNode;
  // Inserts a new empty block at `pos` (a top-level document offset) and, where it makes sense, puts the cursor in it.
  insert: (editor: Editor, pos: number) => void;
}

const iconClass = "h-5 w-5";

const heading = (level: 1 | 2 | 3) => (editor: Editor, pos: number) =>
  editor.chain().insertContentAt(pos, { type: "heading", attrs: { level } }).focus(pos + 1).run();

function buildBlocks(enableImage: boolean): BlockDef[] {
  const blocks: BlockDef[] = [
    {
      id: "image",
      label: "Image",
      icon: <ImageIcon className={iconClass} />,
      insert: (editor, pos) => editor.chain().insertContentAt(pos, { type: "imagePlaceholder" }).run(),
    },
    {
      id: "paragraph",
      label: "Paragraph",
      icon: <Pilcrow className={iconClass} />,
      insert: (editor, pos) => editor.chain().insertContentAt(pos, { type: "paragraph" }).focus(pos + 1).run(),
    },
    { id: "heading", label: "Heading", icon: <Bookmark className={iconClass} />, insert: heading(2) },
    { id: "h1", label: "Heading 1", icon: <Heading1 className={iconClass} />, insert: heading(1) },
    { id: "h2", label: "Heading 2", icon: <Heading2 className={iconClass} />, insert: heading(2) },
    { id: "h3", label: "Heading 3", icon: <Heading3 className={iconClass} />, insert: heading(3) },
    {
      id: "bullet",
      label: "Bullet list",
      icon: <List className={iconClass} />,
      insert: (editor, pos) =>
        editor
          .chain()
          .insertContentAt(pos, { type: "bulletList", content: [{ type: "listItem", content: [{ type: "paragraph" }] }] })
          .focus(pos + 3)
          .run(),
    },
    {
      id: "ordered",
      label: "Numbered list",
      icon: <ListOrdered className={iconClass} />,
      insert: (editor, pos) =>
        editor
          .chain()
          .insertContentAt(pos, { type: "orderedList", content: [{ type: "listItem", content: [{ type: "paragraph" }] }] })
          .focus(pos + 3)
          .run(),
    },
    {
      id: "quote",
      label: "Quote",
      icon: <Quote className={iconClass} />,
      insert: (editor, pos) =>
        editor
          .chain()
          .insertContentAt(pos, { type: "blockquote", content: [{ type: "paragraph" }] })
          .focus(pos + 2)
          .run(),
    },
    {
      id: "divider",
      label: "Divider",
      icon: <Minus className={iconClass} />,
      insert: (editor, pos) => editor.chain().insertContentAt(pos, { type: "horizontalRule" }).focus().run(),
    },
  ];
  return enableImage ? blocks : blocks.filter((b) => b.id !== "image");
}

interface Boundary {
  index: number; // position among the document's top-level blocks (0 = before the first)
  y: number; // viewport Y of the gap
}

const HOVER_THRESHOLD_PX = 14;
const COMPACT_COUNT = 6;

// Gutenberg-style "add a block here" control: hovering the gap between two
// blocks shows a "+" on a blue line; clicking it opens a searchable list of
// blocks and inserts the chosen one exactly at that gap.
export default function BlockInserter({
  editor,
  containerRef,
  enableImage,
}: {
  editor: Editor;
  containerRef: React.RefObject<HTMLDivElement | null>;
  enableImage: boolean;
}) {
  const blocks = useMemo(() => buildBlocks(enableImage), [enableImage]);
  const [hover, setHover] = useState<{ index: number; top: number } | null>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [browseAll, setBrowseAll] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const boundaries = useCallback((): Boundary[] => {
    const list: Boundary[] = [];
    let prevBottom: number | null = null;
    let index = 0;
    editor.state.doc.forEach((_node, offset) => {
      const el = editor.view.nodeDOM(offset) as HTMLElement | null;
      if (el && typeof el.getBoundingClientRect === "function") {
        const r = el.getBoundingClientRect();
        list.push({ index, y: prevBottom === null ? r.top - 6 : (prevBottom + r.top) / 2 });
        prevBottom = r.bottom;
      }
      index += 1;
    });
    if (prevBottom !== null) list.push({ index, y: prevBottom + 6 });
    return list;
  }, [editor]);

  const posForIndex = useCallback(
    (index: number) => {
      let pos = editor.state.doc.content.size;
      let i = 0;
      editor.state.doc.forEach((_node, offset) => {
        if (i === index) pos = offset;
        i += 1;
      });
      return pos;
    },
    [editor]
  );

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setBrowseAll(false);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const onMove = (e: MouseEvent) => {
      if (open) return;
      const containerTop = container.getBoundingClientRect().top;
      let best: Boundary | null = null;
      for (const b of boundaries()) {
        if (Math.abs(b.y - e.clientY) <= HOVER_THRESHOLD_PX && (!best || Math.abs(b.y - e.clientY) < Math.abs(best.y - e.clientY))) {
          best = b;
        }
      }
      setHover(best ? { index: best.index, top: best.y - containerTop } : null);
    };
    const onLeave = () => {
      if (!open) setHover(null);
    };
    container.addEventListener("mousemove", onMove);
    container.addEventListener("mouseleave", onLeave);
    return () => {
      container.removeEventListener("mousemove", onMove);
      container.removeEventListener("mouseleave", onLeave);
    };
  }, [containerRef, boundaries, open]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        close();
        setHover(null);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        close();
        setHover(null);
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close]);

  const searching = query.trim() !== "";
  const visible = searching
    ? blocks.filter((b) => b.label.toLowerCase().includes(query.trim().toLowerCase()))
    : browseAll
      ? blocks
      : blocks.slice(0, COMPACT_COUNT);

  const choose = (block: BlockDef) => {
    if (!hover) return;
    block.insert(editor, posForIndex(hover.index));
    close();
    setHover(null);
  };

  if (!hover) return null;

  return (
    <div ref={rootRef} className="pointer-events-none absolute inset-x-0 z-20" style={{ top: hover.top }}>
      <div className="relative flex -translate-y-1/2 items-center justify-center">
        <span className={`block w-14 ${open ? "h-0.5 bg-brand-500" : "h-px bg-gray-300 dark:bg-gray-600"}`} />
        <button
          type="button"
          aria-label={open ? "Close block inserter" : "Add block"}
          title={open ? "Close" : "Add block"}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => (open ? close() : setOpen(true))}
          className="pointer-events-auto flex h-6 w-6 items-center justify-center bg-brand-500 text-white hover:bg-brand-600"
        >
          {open ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
        </button>
        <span className={`block w-14 ${open ? "h-0.5 bg-brand-500" : "h-px bg-gray-300 dark:bg-gray-600"}`} />
      </div>

      {open && (
        <div
          role="dialog"
          aria-label="Block inserter"
          className="pointer-events-auto absolute left-1/2 top-4 z-30 w-[340px] max-w-[calc(100%-16px)] -translate-x-1/2 overflow-hidden rounded-md border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-900"
        >
          <div className="p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-500" />
              <input
                autoFocus
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && visible[0]) {
                    e.preventDefault();
                    choose(visible[0]);
                  }
                }}
                placeholder="Search"
                aria-label="Search blocks"
                className="h-9 w-full rounded-sm border border-brand-500 bg-white pl-8 pr-2 text-xs text-gray-800 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-900 dark:text-gray-100"
              />
            </div>
          </div>
          <div className="max-h-64 overflow-y-auto px-3 pb-3">
            {visible.length === 0 ? (
              <p className="py-6 text-center text-xs text-gray-400">No blocks found.</p>
            ) : (
              <div className="grid grid-cols-3 gap-y-3">
                {visible.map((block) => (
                  <button
                    key={block.id}
                    type="button"
                    onClick={() => choose(block)}
                    className="flex flex-col items-center gap-2 rounded-md px-1 py-3 text-[11px] font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-white/10"
                  >
                    {block.icon}
                    {block.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          {!searching && blocks.length > COMPACT_COUNT && (
            <button
              type="button"
              onClick={() => setBrowseAll((v) => !v)}
              className="w-full bg-gray-900 py-3 text-xs font-semibold text-white hover:bg-black"
            >
              {browseAll ? "Show fewer" : "Browse all"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
