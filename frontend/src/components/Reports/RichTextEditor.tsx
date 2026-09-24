import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import type { Node as PMNode } from "@tiptap/pm/model";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import TextAlign from "@tiptap/extension-text-align";
import Image from "@tiptap/extension-image";
import {
  AlignCenter,
  AlignLeft,
  AlignRight,
  Bold,
  Heading1,
  Heading2,
  Heading3,
  Italic,
  Link as LinkIcon,
  List,
  ListOrdered,
  Quote,
  Strikethrough,
  Undo2,
  Redo2,
} from "lucide-react";

import BlockInserter from "./editorBlocks/BlockInserter";
import { InsertTableMenu, TableToolsBar, flattenPastedTables, tableExtensions } from "./editorBlocks/tableSupport";
import { ImagePlaceholder, stripImagePlaceholders, type EditorImageHandlers } from "./editorBlocks/ImagePlaceholderNode";

interface RichTextEditorProps {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  // Off by default (comments have no business with headings) — blog post
  // body editing and the content structure checker turn this on (H1-H3).
  headings?: boolean;
  // Turns on the Gutenberg-style block inserter (a "+" between blocks) and
  // the Image block, which needs somewhere to upload to and a library to
  // pick from. Blog post editing passes this; comments never do.
  imageBlocks?: EditorImageHandlers;
}

// Exposed so a caller that's about to save can read the editor's CURRENT
// content directly (`ref.current?.getHTML()`) instead of trusting `value`
// to have caught up via onChange -> setState -> re-render first. Found via
// real testing, not theoretical: that round trip has a real timing gap
// around rapid-fire edit-then-immediately-save sequences (confirmed with
// plain typing too, nothing specific to any one toolbar button) where a
// save could fire before the parent's own state had caught up to the
// editor's actual content, saving stale content. Reading straight from the
// live editor instance sidesteps that gap entirely rather than trying to
// close it.
export interface RichTextEditorHandle {
  getHTML: () => string;
}

function ToolbarButton({
  onClick,
  active,
  disabled,
  label,
  children,
}: {
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onMouseDown={(e) => e.preventDefault()} // keep editor selection/focus while clicking toolbar
      onClick={onClick}
      className={`flex h-7 w-7 items-center justify-center rounded-md transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        active
          ? "bg-brand-500 text-white"
          : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
      }`}
    >
      {children}
    </button>
  );
}

const RichTextEditor = forwardRef<RichTextEditorHandle, RichTextEditorProps>(function RichTextEditor(
  { value, onChange, placeholder, headings = false, imageBlocks },
  ref
) {
  // The last html *we* emitted via onChange — lets the resync effect below
  // tell "the parent handed back the value we just gave it" (an echo of
  // our own edit, arriving as this render's `value` prop after the
  // onChange -> setState -> re-render round trip) apart from "the parent
  // genuinely reset `value` to something else" (e.g. cancel/reload).
  const lastEmittedRef = useRef(value);

  // The editor (and so its extensions) is built once, but the caller's upload/
  // library callbacks close over things like the selected site — read them
  // through a ref so the extension never holds a stale copy.
  const imageBlocksRef = useRef(imageBlocks);
  imageBlocksRef.current = imageBlocks;
  const containerRef = useRef<HTMLDivElement>(null);
  // Set when a paste just had its table(s) flattened into plain blocks, so the "first line is a title" rule below leaves that paste alone.
  const pastedTableRef = useRef(false);
  const serialize = (ed: { isEmpty: boolean; getHTML: () => string }) =>
    ed.isEmpty ? "" : stripImagePlaceholders(ed.getHTML());

  // useEditor's options object (including `content`) is rebuilt on every
  // render and handed to @tiptap/react's own EditorInstanceManager, which
  // keeps a ref to "the latest options" and — independently of the resync
  // effect below, entirely inside the library — re-applies it via
  // editor.setOptions() a tick after render (its scheduleDestroy/onRender
  // bookkeeping; see node_modules/@tiptap/react/dist/index.cjs). That
  // re-apply includes whatever `content` happened to be in the options
  // object AT THAT MOMENT. Real bug this caused, found by testing (not
  // theoretical): passing the live `value` prop as `content` here meant
  // every such re-apply could reset the document back to a `value` that
  // hadn't caught up yet — invisible while actively typing (each keystroke
  // re-renders fast enough to keep superseding it), but it would win the
  // moment typing paused, e.g. right before a Save click, quietly
  // reverting content that had just been typed. `content` is only ever
  // meant to seed the editor once; ongoing sync already goes through the
  // explicit setContent() effect below, which is the one place this
  // component is allowed to change the document after that.
  const initialContentRef = useRef(value || "");

  const editor = useEditor({
    extensions: [
      // H1 is allowed: generated posts carry their own single <h1> in the
      // body, and the structure checker counts H1s. With levels [2, 3] a
      // pasted <h1> was silently turned into a plain paragraph — so it
      // rendered small and was counted as 0 H1s.
      StarterKit.configure({ heading: headings ? { levels: [1, 2, 3] } : false }),
      Link.configure({ openOnClick: false, autolink: true, HTMLAttributes: { rel: "noopener noreferrer" } }),
      Placeholder.configure({ placeholder: placeholder ?? "Write a comment…" }),
      TextAlign.configure({ types: ["heading", "paragraph"] }),
      ...(headings ? tableExtensions : []),
      ...(imageBlocks
        ? [
            Image.configure({ inline: false }),
            ImagePlaceholder.configure({
              uploadImage: (file: File) => imageBlocksRef.current!.uploadImage(file),
              listLibrary: () => imageBlocksRef.current!.listLibrary(),
            }),
          ]
        : []),
    ],
    content: initialContentRef.current,
    onUpdate: ({ editor }) => {
      const html = serialize(editor);
      lastEmittedRef.current = html;
      onChange(html);
    },
    editorProps: {
      // A table copied from Word / Google Docs / a web page comes in as plain
      // blocks (one per cell, in reading order) instead of turning into an editor
      // table on its own; select it and use Insert table to put it in a table.
      // Tables copied from this editor keep their structure.
      transformPastedHTML: headings
        ? (html: string) => {
            const flattened = flattenPastedTables(html);
            pastedTableRef.current = flattened !== html;
            return flattened;
          }
        : undefined,
      // Text copied from a chat, a doc or a web page usually arrives with its
      // title as a plain/styled paragraph — no <h1> tag survives the copy —
      // so it landed as small body text and counted as 0 H1s. When a whole
      // article is pasted into an EMPTY heading-enabled editor and its first
      // line looks like a title (one short line, no closing full stop,
      // followed by more content), that line becomes the H1. Anything that
      // already carries its own <h1> is left exactly as pasted — and so is a
      // paste whose table was just flattened, since its first cell is a
      // column heading, not a page title.
      handlePaste: headings
        ? (view, _event, slice) => {
            if (pastedTableRef.current) {
              pastedTableRef.current = false;
              return false;
            }
            const { doc, schema, tr } = view.state;
            if (doc.textContent.trim() !== "" || doc.childCount > 1) return false;
            const blocks: PMNode[] = [];
            slice.content.forEach((node) => blocks.push(node));
            if (blocks.length < 2 || blocks[0].type.name !== "paragraph") return false;
            if (blocks.some((n) => n.type.name === "heading" && n.attrs.level === 1)) return false;
            const titleText = blocks[0].textContent.trim();
            if (titleText.length < 3 || titleText.length > 150 || titleText.endsWith(".")) return false;
            blocks[0] = schema.nodes.heading.create({ level: 1 }, blocks[0].content);
            view.dispatch(tr.replaceWith(0, doc.content.size, blocks).scrollIntoView());
            return true;
          }
        : undefined,
      attributes: {
        class:
          "prose prose-sm max-w-none px-3 py-2 text-sm text-gray-700 dark:text-gray-200 focus:outline-none min-h-[80px] [&_img]:h-auto [&_img]:max-w-full [&_img.ProseMirror-selectednode]:outline [&_img.ProseMirror-selectednode]:outline-2 [&_img.ProseMirror-selectednode]:outline-brand-500",
      },
    },
  });

  // Keep the editor in sync if the parent resets `value` (e.g. form reset on close) —
  // but not when `value` is just our own last edit echoed back.
  useEffect(() => {
    if (!editor || value === lastEmittedRef.current) return;
    if (value !== serialize(editor) && !(value === "" && editor.isEmpty)) {
      lastEmittedRef.current = value;
      editor.commands.setContent(value || "", false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  useImperativeHandle(
    ref,
    () => ({
      getHTML: () => (editor ? serialize(editor) : value),
    }),
    [editor, value]
  );

  if (!editor) return null;

  const setLink = () => {
    const previous = editor.getAttributes("link").href as string | undefined;
    const url = window.prompt("Link URL", previous ?? "https://");
    if (url === null) return;
    if (url === "") {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
  };

  return (
    <div className="rounded-lg border border-gray-300 bg-white dark:border-gray-700 dark:bg-gray-900">
      <div className="flex items-center gap-0.5 rounded-t-lg border-b border-gray-100 px-2 py-1 dark:border-gray-800">
        {headings && (
          <>
            <ToolbarButton
              label="Heading 1"
              active={editor.isActive("heading", { level: 1 })}
              onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            >
              <Heading1 className="h-3.5 w-3.5" />
            </ToolbarButton>
            <ToolbarButton
              label="Heading 2"
              active={editor.isActive("heading", { level: 2 })}
              onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            >
              <Heading2 className="h-3.5 w-3.5" />
            </ToolbarButton>
            <ToolbarButton
              label="Heading 3"
              active={editor.isActive("heading", { level: 3 })}
              onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            >
              <Heading3 className="h-3.5 w-3.5" />
            </ToolbarButton>
            <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />
          </>
        )}
        <ToolbarButton
          label="Bold"
          active={editor.isActive("bold")}
          onClick={() => editor.chain().focus().toggleBold().run()}
        >
          <Bold className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton
          label="Italic"
          active={editor.isActive("italic")}
          onClick={() => editor.chain().focus().toggleItalic().run()}
        >
          <Italic className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton
          label="Strikethrough"
          active={editor.isActive("strike")}
          onClick={() => editor.chain().focus().toggleStrike().run()}
        >
          <Strikethrough className="h-3.5 w-3.5" />
        </ToolbarButton>
        <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />
        <ToolbarButton
          label="Bullet list"
          active={editor.isActive("bulletList")}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        >
          <List className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton
          label="Numbered list"
          active={editor.isActive("orderedList")}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
        >
          <ListOrdered className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton
          label="Quote"
          active={editor.isActive("blockquote")}
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
        >
          <Quote className="h-3.5 w-3.5" />
        </ToolbarButton>
        <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />
        <ToolbarButton
          label="Align left"
          active={editor.isActive({ textAlign: "left" })}
          onClick={() => editor.chain().focus().setTextAlign("left").run()}
        >
          <AlignLeft className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton
          label="Align center"
          active={editor.isActive({ textAlign: "center" })}
          onClick={() => editor.chain().focus().setTextAlign("center").run()}
        >
          <AlignCenter className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton
          label="Align right"
          active={editor.isActive({ textAlign: "right" })}
          onClick={() => editor.chain().focus().setTextAlign("right").run()}
        >
          <AlignRight className="h-3.5 w-3.5" />
        </ToolbarButton>
        <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />
        <ToolbarButton label="Link" active={editor.isActive("link")} onClick={setLink}>
          <LinkIcon className="h-3.5 w-3.5" />
        </ToolbarButton>
        {headings && <InsertTableMenu editor={editor} />}
        <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />
        <ToolbarButton
          label="Undo"
          disabled={!editor.can().undo()}
          onClick={() => editor.chain().focus().undo().run()}
        >
          <Undo2 className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton
          label="Redo"
          disabled={!editor.can().redo()}
          onClick={() => editor.chain().focus().redo().run()}
        >
          <Redo2 className="h-3.5 w-3.5" />
        </ToolbarButton>
      </div>
      {headings && <TableToolsBar editor={editor} />}
      <div ref={containerRef} className="relative">
        <EditorContent editor={editor} />
        {imageBlocks && <BlockInserter editor={editor} containerRef={containerRef} enableImage />}
      </div>
    </div>
  );
});

export default RichTextEditor;
