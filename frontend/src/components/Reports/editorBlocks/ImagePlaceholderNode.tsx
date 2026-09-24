import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Node, NodeViewWrapper, ReactNodeViewRenderer, type NodeViewProps } from "@tiptap/react";
import type { AxiosError } from "axios";
import { Image as ImageIcon, Loader2, X } from "lucide-react";

import ProgressBar from "@/components/common/ProgressBar";
import { Modal } from "@/components/ui/modal";

export interface EditorImageHandlers {
  uploadImage: (file: File) => Promise<string>;
  listLibrary: () => Promise<{ url: string }[]>;
}

function errorMessage(err: unknown, fallback: string): string {
  const detail = (err as AxiosError<{ detail?: string }>)?.response?.data?.detail;
  return detail || (err instanceof Error && err.message) || fallback;
}

function LibraryModal({
  listLibrary,
  onPick,
  onClose,
}: {
  listLibrary: EditorImageHandlers["listLibrary"];
  onPick: (url: string) => void;
  onClose: () => void;
}) {
  const [images, setImages] = useState<{ url: string }[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listLibrary()
      .then((rows) => !cancelled && setImages(rows))
      .catch((err) => !cancelled && setError(errorMessage(err, "Could not load the media library.")));
    return () => {
      cancelled = true;
    };
  }, [listLibrary]);

  return createPortal(
    <Modal isOpen onClose={onClose} className="max-w-3xl p-6">
      <h3 className="mb-1 text-lg font-semibold text-gray-900 dark:text-white">Media Library</h3>
      <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
        Images already published for this site through the app. Pick one to insert it.
      </p>
      {error ? (
        <p className="text-sm text-error-500">{error}</p>
      ) : images === null ? (
        <div className="flex h-32 items-center justify-center text-gray-400">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : images.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">
          No images yet — upload one first and it will show up here.
        </p>
      ) : (
        <div className="grid max-h-[60vh] grid-cols-2 gap-3 overflow-y-auto sm:grid-cols-3 md:grid-cols-4">
          {images.map((img) => (
            <button
              key={img.url}
              type="button"
              onClick={() => onPick(img.url)}
              className="aspect-video overflow-hidden rounded-lg border border-gray-200 bg-gray-50 transition hover:ring-2 hover:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
            >
              <img src={img.url} alt="" loading="lazy" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </Modal>,
    document.body
  );
}

function ImagePlaceholderView({ editor, node, getPos, deleteNode, extension }: NodeViewProps) {
  const handlers = extension.options as EditorImageHandlers;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [alt, setAlt] = useState("");
  const [showUrl, setShowUrl] = useState(false);
  const [url, setUrl] = useState("");
  const [showLibrary, setShowLibrary] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const replaceWithImage = (src: string) => {
    const pos = getPos();
    if (typeof pos !== "number") return;
    editor
      .chain()
      .focus()
      .insertContentAt({ from: pos, to: pos + node.nodeSize }, { type: "image", attrs: { src, alt: alt.trim() || null } })
      .run();
  };

  const upload = async (file: File | undefined) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Please choose an image file.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      replaceWithImage(await handlers.uploadImage(file));
    } catch (err) {
      setError(errorMessage(err, "Upload failed."));
      setBusy(false);
    }
  };

  const insertFromUrl = () => {
    const trimmed = url.trim();
    if (!/^https?:\/\/\S+$/i.test(trimmed)) {
      setError("Enter a full image URL starting with http:// or https://");
      return;
    }
    replaceWithImage(trimmed);
  };

  return (
    <NodeViewWrapper className="my-4">
      <div
        contentEditable={false}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          void upload(e.dataTransfer.files?.[0]);
        }}
        className="relative rounded-sm border border-gray-900 bg-white p-5 text-gray-800 dark:border-gray-500 dark:bg-gray-900 dark:text-gray-100"
      >
        <button
          type="button"
          aria-label="Remove image block"
          title="Remove image block"
          onClick={() => deleteNode()}
          className="absolute right-2 top-2 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-white/10"
        >
          <X className="h-4 w-4" />
        </button>
        <p className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <ImageIcon className="h-5 w-5" /> Image
        </p>
        <p className="mb-3 text-xs text-gray-600 dark:text-gray-300">
          Drag and drop an image, upload, or choose from your library.
        </p>

        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            void upload(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => fileRef.current?.click()}
            className="rounded-md bg-brand-500 px-4 py-2 text-xs font-semibold text-white hover:bg-brand-600 disabled:opacity-60"
          >
            Upload
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => setShowLibrary(true)}
            className="rounded-md border border-brand-500 px-4 py-2 text-xs font-semibold text-brand-600 hover:bg-brand-50 disabled:opacity-60 dark:hover:bg-brand-500/10"
          >
            Media Library
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => setShowUrl((v) => !v)}
            className="rounded-md border border-brand-500 px-4 py-2 text-xs font-semibold text-brand-600 hover:bg-brand-50 disabled:opacity-60 dark:hover:bg-brand-500/10"
          >
            Insert from URL
          </button>
        </div>

        {showUrl && (
          <div className="mt-3 flex flex-wrap gap-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && insertFromUrl()}
              placeholder="https://example.com/image.jpg"
              aria-label="Image URL"
              className="h-9 min-w-0 flex-1 rounded-md border border-gray-300 bg-white px-3 text-xs text-gray-800 focus:border-brand-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            />
            <button
              type="button"
              onClick={insertFromUrl}
              className="rounded-md bg-brand-500 px-4 text-xs font-semibold text-white hover:bg-brand-600"
            >
              Insert
            </button>
          </div>
        )}

        <input
          type="text"
          value={alt}
          onChange={(e) => setAlt(e.target.value)}
          placeholder="Alt text (recommended for SEO and accessibility)"
          aria-label="Image alt text"
          className="mt-3 h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-xs text-gray-800 focus:border-brand-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
        />

        {busy && (
          <div className="mt-3 space-y-1">
            <ProgressBar />
            <p className="text-xs text-gray-500">Uploading and converting to WebP…</p>
          </div>
        )}
        {error && <p className="mt-3 text-xs text-error-500">{error}</p>}
      </div>

      {showLibrary && (
        <LibraryModal
          listLibrary={handlers.listLibrary}
          onClose={() => setShowLibrary(false)}
          onPick={(picked) => {
            setShowLibrary(false);
            replaceWithImage(picked);
          }}
        />
      )}
    </NodeViewWrapper>
  );
}

// The placeholder only exists while the user is choosing an image; it is
// swapped for a real <img> node the moment one is picked. If it's ever left
// unresolved it must not leak into saved content, so serialization strips
// it (stripImagePlaceholders) rather than trusting renderHTML to be inert.
export const ImagePlaceholder = Node.create<EditorImageHandlers>({
  name: "imagePlaceholder",
  group: "block",
  atom: true,
  selectable: false,
  draggable: false,

  addOptions() {
    return {
      uploadImage: async () => {
        throw new Error("Image upload isn't configured here.");
      },
      listLibrary: async () => [],
    };
  },

  parseHTML() {
    return [];
  },

  renderHTML() {
    return ["div", { "data-image-placeholder": "" }];
  },

  addNodeView() {
    return ReactNodeViewRenderer(ImagePlaceholderView, { stopEvent: () => true });
  },
});

export const stripImagePlaceholders = (html: string) =>
  html.replace(/<div data-image-placeholder[^>]*><\/div>/g, "");
