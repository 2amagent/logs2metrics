"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/pending", label: "pending" },
  { href: "/categorized", label: "categorized" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--line)] bg-[var(--bg-raised)]/95 backdrop-blur-sm">
      <div className="mx-auto max-w-5xl px-5 py-3 flex items-center gap-6">
        <Link href="/pending" className="flex items-center gap-2.5 shrink-0">
          <span
            className="inline-block w-2 h-2 rounded-full bg-[var(--accent)]"
            style={{ animation: "blink 2.4s ease-in-out infinite", boxShadow: "0 0 6px var(--accent)" }}
          />
          <span
            className="tracking-tight text-[15px] leading-none"
            style={{ fontFamily: "var(--font-display)" }}
          >
            log-triage
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-[12px]">
          {links.map((link) => {
            const active = pathname?.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3 py-1.5 border-b-2 transition-colors ${
                  active
                    ? "text-[var(--ink)] border-[var(--accent)]"
                    : "text-[var(--ink-dim)] border-transparent hover:text-[var(--ink)]"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
