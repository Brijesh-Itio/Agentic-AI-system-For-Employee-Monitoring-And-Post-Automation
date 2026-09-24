import { createContext, useContext } from "react";

// Pages the layout keeps mounted-but-hidden (see KeepAliveOutlet) still render
// while another page is on screen. Anything that must only act for the page
// the user is actually looking at — the browser tab title, for one — reads this.
const PageActiveContext = createContext(true);

export const PageActiveProvider = PageActiveContext.Provider;
export const usePageActive = () => useContext(PageActiveContext);
