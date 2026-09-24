import { useEffect } from "react";
import { HelmetProvider, Helmet } from "react-helmet-async";

import { usePageActive } from "@/context/PageActiveContext";

// Pages kept alive in the background (see layout/KeepAliveOutlet) stay
// mounted, so only the page actually on screen may set the browser tab title.
// The title is set straight on document.title rather than through <Helmet>:
// react-helmet-async stopped reliably picking up the change when several
// pages were mounted at once (the title stuck on whichever page came before).
// Helmet still carries the description meta.
const PageMeta = ({
  title,
  description,
}: {
  title: string;
  description: string;
}) => {
  const active = usePageActive();

  useEffect(() => {
    if (active) document.title = title;
  }, [active, title]);

  if (!active) return null;
  return (
    <Helmet>
      <meta name="description" content={description} />
    </Helmet>
  );
};

export const AppWrapper = ({ children }: { children: React.ReactNode }) => (
  <HelmetProvider>{children}</HelmetProvider>
);

export default PageMeta;
