import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Editor } from "@tiptap/react";
import type { Node as PMNode } from "@tiptap/pm/model";
import { AllSelection, TextSelection } from "@tiptap/pm/state";
import Table from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import {
  BetweenHorizontalEnd,
  BetweenHorizontalStart,
  BetweenVerticalEnd,
  BetweenVerticalStart,
  Table2,
  TableCellsMerge,
  TableCellsSplit,
  Trash2,
} from "lucide-react";

export type TableBorders = "all" | "outside" | "inside" | "horizontal" | "vertical" | "none" | "topbottom" | "leftright";

// Which of the four line groups each preset draws: outer edges (horizontal =
// top/bottom, vertical = left/right) and the lines between cells.
const PRESETS: { id: TableBorders; label: string; outerH: boolean; outerV: boolean; innerH: boolean; innerV: boolean }[] = [
  { id: "all", label: "All borders", outerH: true, outerV: true, innerH: true, innerV: true },
  { id: "outside", label: "Outside borders", outerH: true, outerV: true, innerH: false, innerV: false },
  { id: "inside", label: "Inside borders", outerH: false, outerV: false, innerH: true, innerV: true },
  { id: "horizontal", label: "Horizontal lines", outerH: true, outerV: false, innerH: true, innerV: false },
  { id: "vertical", label: "Vertical lines", outerH: false, outerV: true, innerH: false, innerV: true },
  { id: "topbottom", label: "Top and bottom border", outerH: true, outerV: false, innerH: false, innerV: false },
  { id: "leftright", label: "Left and right border", outerH: false, outerV: true, innerH: false, innerV: false },
  { id: "none", label: "No borders", outerH: false, outerV: false, innerH: false, innerV: false },
];

// Saved as the classic HTML table attributes (border/frame/rules) rather than
// CSS: they render the same in a WordPress/Webflow theme without needing any
// stylesheet from this app. The editor itself draws the same look from the
// data-borders value (see index.css) because Tailwind's reset would otherwise
// hide these attributes.
const LEGACY_ATTRS: Record<TableBorders, { border: string; frame: string; rules: string }> = {
  all: { border: "1", frame: "border", rules: "all" },
  outside: { border: "1", frame: "box", rules: "none" },
  inside: { border: "1", frame: "void", rules: "all" },
  horizontal: { border: "1", frame: "hsides", rules: "rows" },
  vertical: { border: "1", frame: "vsides", rules: "cols" },
  topbottom: { border: "1", frame: "hsides", rules: "none" },
  leftright: { border: "1", frame: "vsides", rules: "none" },
  none: { border: "0", frame: "void", rules: "none" },
};

// `borders` is null for any table this app didn't create (e.g. one that came
// from the CMS): those are re-saved exactly as they were, with no attributes
// added, so a theme's own table styling isn't overridden by an edit.
const BorderedTable = Table.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      borders: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute("data-borders"),
        renderHTML: (attributes: Record<string, unknown>) => {
          const borders = attributes.borders as TableBorders | null;
          if (!borders || !LEGACY_ATTRS[borders]) return {};
          return {
            "data-borders": borders,
            ...LEGACY_ATTRS[borders],
            cellpadding: "8",
            cellspacing: "0",
            style: "width:100%;border-collapse:collapse",
          };
        },
      },
    };
  },
});

export const tableExtensions = [BorderedTable.configure({ resizable: false }), TableRow, TableHeader, TableCell];

// Turns every <table> in pasted HTML into its cells' content, one block per
// cell in reading order (empty cells are skipped), so a table copied from
// Word / Google Docs / a web page pastes as ordinary text instead of becoming
// an editor table. HTML copied out of this editor itself (marked with
// ProseMirror's data-pm-slice) is left alone so our own tables copy-paste
// with their structure. Returns the input string untouched if nothing changed.
export function flattenPastedTables(html: string): string {
  if (!/<table[\s>]/i.test(html) || html.includes("data-pm-slice")) return html;
  const doc = new DOMParser().parseFromString(html, "text/html");
  const blockSelector = "p,div,ul,ol,h1,h2,h3,h4,h5,h6,blockquote,pre";
  // "Empty" includes invisible characters: Docs/Sheets fill spacer cells with
  // zero-width spaces (U+200B) and BOMs, which String.trim() doesn't strip but
  // which still render as a full blank line.
  const invisible = /[\s\u00a0\u200b-\u200d\u2060\ufeff]/g;
  const isBlank = (node: Node) =>
    (node.textContent ?? "").replace(invisible, "") === "" && !(node instanceof Element && node.querySelector("img"));
  // Innermost tables first, so a nested table is already flat by the time its outer cell is read.
  Array.from(doc.querySelectorAll("table"))
    .reverse()
    .forEach((table) => {
      const flat = doc.createDocumentFragment();
      table.querySelectorAll("th, td").forEach((cell) => {
        if (isBlank(cell)) return;
        if (cell.querySelector(blockSelector)) {
          // Cells copied from Google Docs / Word are full of empty spacer
          // paragraphs and <br>s; keep only the parts that hold something.
          Array.from(cell.childNodes).forEach((child) => {
            if (!isBlank(child)) flat.append(child);
          });
        } else {
          const p = doc.createElement("p");
          p.append(...Array.from(cell.childNodes));
          flat.append(p);
        }
      });
      table.replaceWith(flat);
    });
  // The source's cell alignment (Docs centres header cells) means nothing once
  // the cells are ordinary lines — it made some lines jump to the middle.
  doc.body.querySelectorAll<HTMLElement>("[style], [align]").forEach((el) => {
    el.style.removeProperty("text-align");
    el.removeAttribute("align");
  });
  return doc.body.innerHTML;
}

const MAX_ROWS = 6;
const MAX_COLS = 8;

function useOutsideClose(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);
  return ref;
}

function BarButton({
  label,
  onClick,
  disabled,
  active,
  danger,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  danger?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      className={`flex h-7 min-w-7 items-center justify-center gap-1 rounded-md px-1.5 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        active
          ? "bg-brand-500 text-white"
          : danger
            ? "text-error-500 hover:bg-error-50 dark:hover:bg-error-500/10"
            : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
      }`}
    >
      {children}
    </button>
  );
}

// Toolbar button: hover a size in the grid, click to insert that many rows x
// columns (first row is a header row, "All borders" is the default look).
export function InsertTableMenu({ editor }: { editor: Editor }) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState({ r: 0, c: 0 });
  const ref = useOutsideClose(open, () => setOpen(false));

  // Selected text -> table: each selected block (paragraph, heading, ...)
  // becomes one cell, filled left to right then top to bottom, and the
  // selection is replaced by the table. Rows are added if the content needs
  // more cells than the size that was picked, so nothing is ever dropped.
  // Returns false (and does nothing) when the selection isn't plain top-level
  // text, so the caller falls back to inserting an empty table.
  const fillTableFromSelection = (rows: number, cols: number): boolean => {
    const { state, view } = editor;
    const { selection, schema } = state;
    const { $from, $to } = selection;
    // Select-all (AllSelection) counts too: the whole document becomes the table's content.
    const wholeDoc = selection instanceof AllSelection;
    if (selection.empty || (!wholeDoc && ($from.depth !== 1 || $to.depth !== 1))) return false;

    const slice = selection.content();
    const units: PMNode[] = [];
    if (slice.content.firstChild?.isInline) {
      units.push(schema.nodes.paragraph.create(null, slice.content));
    } else {
      slice.content.forEach((node) => {
        if (node.isTextblock && node.content.size === 0) return;
        units.push(node);
      });
    }
    if (units.length === 0 || units.some((n) => n.type.name === "table")) return false;

    const rowCount = Math.max(rows, Math.ceil(units.length / cols));
    const tableRows: PMNode[] = [];
    for (let r = 0; r < rowCount; r += 1) {
      const cells: PMNode[] = [];
      for (let c = 0; c < cols; c += 1) {
        const unit = units[r * cols + c];
        cells.push(schema.nodes.tableCell.create(null, unit ?? schema.nodes.paragraph.create()));
      }
      tableRows.push(schema.nodes.tableRow.create(null, cells));
    }
    const table = schema.nodes.table.create({ borders: "all" }, tableRows);

    // Fully selected end blocks are replaced whole; a partly selected block
    // keeps the text that wasn't selected on its side of the table.
    const from = wholeDoc ? 0 : $from.parentOffset === 0 ? $from.before(1) : $from.pos;
    const to = wholeDoc ? state.doc.content.size : $to.parentOffset === $to.parent.content.size ? $to.after(1) : $to.pos;
    // A table as the very last block leaves nowhere to keep typing, so an empty paragraph follows it.
    const replacement = to >= state.doc.content.size ? [table, schema.nodes.paragraph.create()] : table;
    const tr = state.tr.replaceWith(from, to, replacement);
    if (wholeDoc || $from.parentOffset === 0) {
      tr.setSelection(TextSelection.near(tr.doc.resolve(from + 1), 1));
    }
    view.dispatch(tr.scrollIntoView());
    view.focus();
    return true;
  };

  const insert = (rows: number, cols: number) => {
    if (fillTableFromSelection(rows, cols)) {
      setOpen(false);
      setHover({ r: 0, c: 0 });
      return;
    }
    const { selection, doc } = editor.state;
    const { $to } = selection;
    // depth 1 = a top-level line; an empty paragraph inside a table cell is deeper and must not take the table.
    const onEmptyLine = selection.empty && $to.depth === 1 && $to.parent.isTextblock && $to.parent.content.size === 0;

    if (onEmptyLine) {
      // Nothing to preserve: the table simply takes the empty line's place.
      editor
        .chain()
        .focus()
        .insertTable({ rows, cols, withHeaderRow: true })
        .updateAttributes("table", { borders: "all" })
        .run();
    } else {
      // The default command REPLACES the selection (or splits the paragraph the
      // cursor is in), which deleted the very text people select before
      // inserting a table. Keep everything and add the table right after the
      // top-level block the selection ends in.
      const pos = $to.depth >= 1 ? $to.after(1) : $to.pos;
      const cell = (header: boolean) => ({ type: header ? "tableHeader" : "tableCell", content: [{ type: "paragraph" }] });
      const table = {
        type: "table",
        attrs: { borders: "all" },
        content: Array.from({ length: rows }, (_, r) => ({
          type: "tableRow",
          content: Array.from({ length: cols }, () => cell(r === 0)),
        })),
      };
      // A table as the very last block leaves nowhere to keep typing, so an empty paragraph follows it.
      const nodes = pos >= doc.content.size ? [table, { type: "paragraph" }] : [table];
      editor.chain().focus().insertContentAt(pos, nodes).focus(pos + 4).run();
    }
    setOpen(false);
    setHover({ r: 0, c: 0 });
  };

  return (
    <div ref={ref} className="relative">
      <BarButton label="Insert table" active={open} onClick={() => setOpen((v) => !v)}>
        <Table2 className="h-3.5 w-3.5" />
      </BarButton>
      {open && (
        <div className="absolute left-0 top-full z-30 mt-1 w-max rounded-md border border-gray-200 bg-white p-2 shadow-lg dark:border-gray-700 dark:bg-gray-900">
          <div
            role="grid"
            aria-label="Table size"
            className="grid gap-0.5"
            style={{ gridTemplateColumns: `repeat(${MAX_COLS}, 1.25rem)` }}
            onMouseLeave={() => setHover({ r: 0, c: 0 })}
          >
            {Array.from({ length: MAX_ROWS * MAX_COLS }, (_, i) => {
              const r = Math.floor(i / MAX_COLS) + 1;
              const c = (i % MAX_COLS) + 1;
              const lit = r <= hover.r && c <= hover.c;
              return (
                <button
                  key={i}
                  type="button"
                  aria-label={`${r} by ${c} table`}
                  onMouseEnter={() => setHover({ r, c })}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => insert(r, c)}
                  className={`h-5 w-5 rounded-sm border ${
                    lit ? "border-brand-500 bg-brand-100 dark:bg-brand-500/30" : "border-gray-300 dark:border-gray-600"
                  }`}
                />
              );
            })}
          </div>
          <p className="mt-1.5 text-center text-xs text-gray-500 dark:text-gray-400">
            {hover.r ? `${hover.r} × ${hover.c}` : "Insert table"}
          </p>
        </div>
      )}
    </div>
  );
}

// Mini 3x3 cell drawing of a preset: solid dark lines where the preset draws a
// border, faint dotted guides everywhere else — same idea as Word's border picker.
function PresetIcon({ preset }: { preset: (typeof PRESETS)[number] }) {
  const xs = [2, 9, 16, 23];
  const ys = [2, 9, 16, 23];
  const guide = { stroke: "#cbd5e1", strokeDasharray: "1.5 1.5", strokeWidth: 1 };
  const solid = { stroke: "#1f2937", strokeWidth: 1.6 };
  return (
    <svg width="26" height="26" viewBox="0 0 25 25" aria-hidden="true">
      {ys.map((y, i) => {
        const outer = i === 0 || i === ys.length - 1;
        const on = outer ? preset.outerH : preset.innerH;
        return <line key={`h${i}`} x1={2} x2={23} y1={y} y2={y} {...(on ? solid : guide)} />;
      })}
      {xs.map((x, i) => {
        const outer = i === 0 || i === xs.length - 1;
        const on = outer ? preset.outerV : preset.innerV;
        return <line key={`v${i}`} x1={x} x2={x} y1={2} y2={23} {...(on ? solid : guide)} />;
      })}
    </svg>
  );
}

function BorderStyleMenu({ editor }: { editor: Editor }) {
  const [open, setOpen] = useState(false);
  const ref = useOutsideClose(open, () => setOpen(false));
  const current = (editor.getAttributes("table").borders as TableBorders | null) ?? null;

  return (
    <div ref={ref} className="relative">
      <BarButton label="Border style" active={open} onClick={() => setOpen((v) => !v)}>
        <span className="px-0.5">Borders</span>
      </BarButton>
      {open && (
        <div
          role="menu"
          aria-label="Border style"
          className="absolute left-0 top-full z-30 mt-1 grid w-max grid-cols-4 gap-1 rounded-md border border-gray-200 bg-white p-2 shadow-lg dark:border-gray-700 dark:bg-gray-900"
        >
          {PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              role="menuitemradio"
              aria-checked={current === preset.id}
              title={preset.label}
              aria-label={preset.label}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                editor.chain().focus().updateAttributes("table", { borders: preset.id }).run();
                setOpen(false);
              }}
              className={`flex h-9 w-9 items-center justify-center rounded-sm border bg-white dark:bg-gray-800 ${
                current === preset.id ? "border-brand-500 ring-1 ring-brand-500" : "border-gray-200 hover:border-gray-400 dark:border-gray-700"
              }`}
            >
              <PresetIcon preset={preset} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Second toolbar row, shown only while the cursor is inside a table.
export function TableToolsBar({ editor }: { editor: Editor }) {
  if (!editor.isActive("table")) return null;
  const can = editor.can();
  const chain = () => editor.chain().focus();
  return (
    <div
      role="toolbar"
      aria-label="Table tools"
      className="flex flex-wrap items-center gap-0.5 border-b border-gray-100 bg-gray-50 px-2 py-1 dark:border-gray-800 dark:bg-white/5"
    >
      <span className="mr-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400">Table</span>
      <BarButton label="Add row above" disabled={!can.addRowBefore()} onClick={() => chain().addRowBefore().run()}>
        <BetweenHorizontalStart className="h-3.5 w-3.5" />
      </BarButton>
      <BarButton label="Add row below" disabled={!can.addRowAfter()} onClick={() => chain().addRowAfter().run()}>
        <BetweenHorizontalEnd className="h-3.5 w-3.5" />
      </BarButton>
      <BarButton label="Delete row" disabled={!can.deleteRow()} onClick={() => chain().deleteRow().run()}>
        <Trash2 className="h-3.5 w-3.5" /> Row
      </BarButton>
      <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />
      <BarButton label="Add column left" disabled={!can.addColumnBefore()} onClick={() => chain().addColumnBefore().run()}>
        <BetweenVerticalStart className="h-3.5 w-3.5" />
      </BarButton>
      <BarButton label="Add column right" disabled={!can.addColumnAfter()} onClick={() => chain().addColumnAfter().run()}>
        <BetweenVerticalEnd className="h-3.5 w-3.5" />
      </BarButton>
      <BarButton label="Delete column" disabled={!can.deleteColumn()} onClick={() => chain().deleteColumn().run()}>
        <Trash2 className="h-3.5 w-3.5" /> Column
      </BarButton>
      <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />
      <BarButton label="Toggle header row" onClick={() => chain().toggleHeaderRow().run()}>
        Header row
      </BarButton>
      <BarButton label="Merge cells" disabled={!can.mergeCells()} onClick={() => chain().mergeCells().run()}>
        <TableCellsMerge className="h-3.5 w-3.5" />
      </BarButton>
      <BarButton label="Split cell" disabled={!can.splitCell()} onClick={() => chain().splitCell().run()}>
        <TableCellsSplit className="h-3.5 w-3.5" />
      </BarButton>
      <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />
      <BorderStyleMenu editor={editor} />
      <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />
      <BarButton label="Delete table" danger onClick={() => chain().deleteTable().run()}>
        <Trash2 className="h-3.5 w-3.5" /> Table
      </BarButton>
    </div>
  );
}
