import Link from "next/link";

import { ApiStatus } from "@/components/layout/api-status";
import { ThemeToggle } from "@/components/layout/theme-toggle";

const NAV_LINKS = [
  { href: "/overview", label: "Overview" },
  { href: "/scanner", label: "Scanner" },
  { href: "/risk", label: "Risk" },
  { href: "/positions", label: "Positions" },
  { href: "/ai", label: "AI" },
  { href: "/alerts", label: "Alerts" },
];

export function Nav() {
  return (
    <header className="flex items-center justify-between border-b border-border px-4 py-3">
      <nav aria-label="Primary" className="flex items-center gap-4">
        {/* shadcn's CardTitle renders a <div>, not a heading element — no
         * page in this app had a real <h1> anywhere (axe's
         * page-has-heading-one, Phase 18). The persistent nav title is
         * the one element guaranteed to render on every route, so it
         * carries the page's single required <h1> rather than auditing
         * each screen's own top-of-content title individually. */}
        <h1 className="text-sm font-semibold tracking-tight">
          <Link href="/">IDX Swing Trading Assistant</Link>
        </h1>
        <ul className="flex items-center gap-3">
          {NAV_LINKS.map((link) => (
            <li key={link.href}>
              <Link href={link.href} className="text-sm text-muted-foreground hover:text-foreground">
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <div className="flex items-center gap-3">
        <ApiStatus />
        <ThemeToggle />
      </div>
    </header>
  );
}
