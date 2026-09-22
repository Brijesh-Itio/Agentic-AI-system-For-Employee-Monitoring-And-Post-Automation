// Tests the user's exact scenario: generating a blog post, then switching
// SEO sub-tabs (Blog -> Social) *before* generation finishes. SeoPage.tsx
// renders each sub-tab as `{tab === "blog" && <BlogTab .../>}`, so
// switching tabs UNMOUNTS BlogTab — destroying its `generateMutation =
// useMutation({...})` hook instance mid-flight.
//
// Exercises the real @tanstack/query-core MutationObserver this app's
// useMutation() is built on (see useMutation.js: `new MutationObserver
// (client, options)` then `observer.mutate(variables, mutateOptions)`),
// not a guess about what "should" happen. Simulates the unmount the same
// way React does: useMutation subscribes the observer via
// useSyncExternalStore for re-rendering, and React calls the returned
// unsubscribe function on unmount — nothing else is tied to the
// component's lifecycle.
global.window = { addEventListener() {}, removeEventListener() {} };
global.document = { visibilityState: "visible" };

const { QueryClient, MutationObserver } = require("@tanstack/query-core");

async function main() {
  const queryClient = new QueryClient();
  let onSuccessFired = false;
  let onErrorFired = false;
  let invalidateCalled = false;

  const FAKE_GENERATION_MS = 300; // stands in for the real 1-3 minute Ollama call

  const observer = new MutationObserver(queryClient, {
    mutationFn: () => new Promise((resolve) => setTimeout(() => resolve({ id: 1, title: "Generated Post" }), FAKE_GENERATION_MS)),
    onSuccess: () => {
      onSuccessFired = true;
      invalidateCalled = true; // stands in for queryClient.invalidateQueries(...)
    },
    onError: () => {
      onErrorFired = true;
    },
  });

  // Mount BlogTab: React subscribes for re-renders (useSyncExternalStore).
  const unsubscribe = observer.subscribe(() => {});

  // Click "Generate".
  const mutatePromise = observer.mutate(undefined).catch(() => {});

  // Switch to the Social tab a moment later, well before the fake
  // generation finishes — this is exactly BlogTab unmounting.
  await new Promise((r) => setTimeout(r, 50));
  unsubscribe();
  console.log("Unmounted BlogTab (switched to Social tab) while generation was still in flight.");

  await mutatePromise;
  // Give notifyManager's batching a moment to flush.
  await new Promise((r) => setTimeout(r, 20));

  console.log(JSON.stringify({ onSuccessFired, onErrorFired, invalidateCalled }, null, 2));

  const passed = onSuccessFired && invalidateCalled && !onErrorFired;
  console.log(`\nGeneration completed and its onSuccess (toast + refresh the post list) ran even after the tab switch: ${passed}`);
  process.exit(passed ? 0 : 1);
}

main();
