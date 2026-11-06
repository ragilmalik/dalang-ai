import { ViewTransition, type ReactNode } from "react";

/**
 * Page transitions. A template (unlike the layout) remounts on every navigation, so the page that leaves and the page
 * that arrives each get a <ViewTransition>: the old page fades down and out fast, the new one rises in a moment later
 * (CSS in globals.css, "Page transitions"). The site header is anchored with its own view-transition-name so it never
 * slides. default="none" keeps every other update on the page (progress, votes, toasts) from triggering a fade.
 * Browsers without the View Transitions API just swap pages, exactly as before. Reduced motion turns it off.
 */
export default function Template({ children }: { children: ReactNode }) {
  return (
    <ViewTransition enter="page-in" exit="page-out" default="none">
      {children}
    </ViewTransition>
  );
}
