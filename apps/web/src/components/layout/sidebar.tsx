"use client";

import { Bell, Briefcase, LayoutDashboard, Radar, Shield, Sparkles } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ApiStatus } from "@/components/layout/api-status";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/scanner", label: "Scanner", icon: Radar },
  { href: "/risk", label: "Risk", icon: Shield },
  { href: "/positions", label: "Positions", icon: Briefcase },
  { href: "/ai", label: "AI", icon: Sparkles },
  { href: "/alerts", label: "Alerts", icon: Bell },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 flex h-screen w-56 shrink-0 flex-col border-r border-border">
      <div className="border-b border-border px-4 py-3">
        {/* shadcn's CardTitle renders a <div>, not a heading element — no
         * page in this app had a real <h1> anywhere (axe's
         * page-has-heading-one, Phase 18). This is the one element
         * guaranteed to render on every route, so it carries the page's
         * single required <h1> rather than auditing each screen's own
         * top-of-content title individually. */}
        <h1 className="text-sm font-semibold tracking-tight">
          <Link href="/">IDX Swing Trading Assistant</Link>
        </h1>
      </div>

      <nav aria-label="Primary" className="flex flex-1 flex-col gap-0.5 p-2">
        {NAV_LINKS.map((link) => {
          const isActive = pathname === link.href || pathname?.startsWith(`${link.href}/`);
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition-colors",
                isActive
                  ? "bg-secondary font-medium text-secondary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
              {link.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center justify-between border-t border-border px-3 py-2">
        <ApiStatus />
        <ThemeToggle />
      </div>
    </aside>
  );
}
