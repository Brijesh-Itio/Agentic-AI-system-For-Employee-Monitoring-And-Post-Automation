import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import TextAlign from "@tiptap/extension-text-align";
import {
  AlignCenter,
  AlignLeft,
  AlignRight,
  Bold,
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

interface RichTextEditorProps {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  // Off by default (comments have no business with headings) — blog post
  // body editing turns this on. H1 is deliberately excluded: that's the
  // post's own title field, not something to duplicate inside the body.
  headings?: boolean;
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
  { value, onChange, placeholder, headings = false },
  ref
) {
  // The last html *we* emitted via onChange — lets the resync effect below
  // tell "the parent handed back the value we just gave it" (an echo of
  // our own edit, arriving as this render's `value` prop after the
  // onChange -> setState -> re-render round trip) apart from "the parent
  // genuinely reset `value` to something else" (e.g. cancel/reload).
  const lastEmittedRef = useRef(value);

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
      StarterKit.configure({ heading: headings ? { levels: [2, 3] } : false }),
      Link.configure({ openOnClick: false, autolink: true, HTMLAttributes: { rel: "noopener noreferrer" } }),
      Placeholder.configure({ placeholder: placeholder ?? "Write a comment…" }),
      TextAlign.configure({ types: ["heading", "paragraph"] }),
    ],
    content: initialContentRef.current,
    onUpdate: ({ editor }) => {
      const html = editor.isEmpty ? "" : editor.getHTML();
      lastEmittedRef.current = html;
      onChange(html);
    },
    editorProps: {
      attributes: {
        class:
          "prose prose-sm max-w-none px-3 py-2 text-sm text-gray-700 dark:text-gray-200 focus:outline-none min-h-[80px]",
      },
    },
  });

  // Keep the editor in sync if the parent resets `value` (e.g. form reset on close) —
  // but not when `value` is just our own last edit echoed back.
  useEffect(() => {
    if (!editor || value === lastEmittedRef.current) return;
    if (value !== editor.getHTML() && !(value === "" && editor.isEmpty)) {
      lastEmittedRef.current = value;
      editor.commands.setContent(value || "", false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  useImperativeHandle(
    ref,
    () => ({
      getHTML: () => (editor ? (editor.isEmpty ? "" : editor.getHTML()) : value),
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
    <div className="overflow-hidden rounded-lg border border-gray-300 bg-white dark:border-gray-700 dark:bg-gray-900">
      <div className="flex items-center gap-0.5 border-b border-gray-100 px-2 py-1 dark:border-gray-800">
        {headings && (
          <>
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
      <EditorContent editor={editor} />
    </div>
  );
});

export default RichTextEditor;
