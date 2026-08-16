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
        <Link href="/" className="text-sm font-semibold tracking-tight">
          IDX Swing Trading Assistant
        </Link>
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
