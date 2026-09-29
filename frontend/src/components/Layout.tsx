import { ReactNode } from "react";
import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/ingest", label: "Ingest & Run" },
  { to: "/review", label: "Review Queue" },
  { to: "/clusters", label: "Families" },
  { to: "/codes", label: "Code Registry" },
  { to: "/audit", label: "Audit Trail" },
];

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen lg:flex">
      {/* Left rail — the national registry masthead + nav */}
      <aside className="lg:w-64 lg:fixed lg:inset-y-0 border-b lg:border-b-0 lg:border-r border-hairline bg-surface z-20">
        <div className="px-5 py-5">
          <div className="flex items-center gap-2.5">
            <Emblem />
            <div>
              <div className="font-display text-lg font-bold leading-none text-ink">
                Samanvay
              </div>
              <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-steel">
                One Nation · One Material Code
              </div>
            </div>
          </div>
        </div>
        <nav className="px-3 pb-4 flex lg:flex-col gap-1 overflow-x-auto">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium transition-colors whitespace-nowrap ${
                  isActive
                    ? "bg-ink text-white"
                    : "text-steel hover:bg-paper hover:text-ink"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden lg:block absolute bottom-0 inset-x-0 px-5 py-4 border-t border-hairline">
          <div className="text-[10px] leading-relaxed text-steel">
            SIH 2026 · PS 26099
            <br />
            Material code de-duplication for CPSEs
          </div>
        </div>
      </aside>

      <main className="lg:ml-64 flex-1 min-w-0">
        <div className="mx-auto max-w-6xl px-5 py-8">{children}</div>
      </main>
    </div>
  );
}

export function PageHead({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1 className="mt-1 font-display text-2xl font-semibold text-ink">
          {title}
        </h1>
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </header>
  );
}

/** A minimal ashoka-chakra-inspired mark — 24 spokes in the national ink. */
function Emblem() {
  const spokes = Array.from({ length: 24 }, (_, i) => i * 15);
  return (
    <svg width="34" height="34" viewBox="0 0 100 100" aria-hidden className="shrink-0">
      <circle cx="50" cy="50" r="46" fill="none" stroke="#12233D" strokeWidth="5" />
      <circle cx="50" cy="50" r="7" fill="#0E7C66" />
      {spokes.map((deg) => (
        <line
          key={deg}
          x1="50"
          y1="50"
          x2="50"
          y2="8"
          stroke="#12233D"
          strokeWidth="2"
          transform={`rotate(${deg} 50 50)`}
          opacity={0.55}
        />
      ))}
    </svg>
  );
}
