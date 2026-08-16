import {
  faBookOpen,
  faChartLine,
  faChartPie,
  faClock,
  faGlobeAmericas,
  faHeadphones,
  faLocationDot,
  faMapLocationDot,
  faSignal,
  faUserGroup,
  faWaveSquare,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { Link, useSearchParams } from "react-router";

import type { Route } from "./+types/admin.usage";
import { Icon } from "~/components/Icon";
import { cloudflare } from "~/context";
import type { UsageKind } from "~/server/analytics.server";
import { usageDashboard } from "~/server/analytics.server";

type UsageView = "overview" | "activity" | "people" | "content" | "countries";
type UsageData = Route.ComponentProps["loaderData"];

const USAGE_TABS: { key: UsageView; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "activity", label: "Activity" },
  { key: "people", label: "People" },
  { key: "content", label: "Content" },
  { key: "countries", label: "Countries" },
];

export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  return usageDashboard(env.DB);
}

export default function AdminUsage({ loaderData }: Route.ComponentProps) {
  const [searchParams] = useSearchParams();
  const view = usageView(searchParams.get("view"));
  const totalSignals =
    loaderData.overview.readingSignals + loaderData.overview.listeningSignals;
  const topCountry = loaderData.countries[0]?.name ?? "No countries yet";
  const topTitle = loaderData.content[0]?.title ?? "No activity yet";
  const maxCountrySignals = Math.max(
    ...loaderData.countries.map((c) => c.signals),
    1,
  );
  const maxContentSignals = Math.max(
    ...loaderData.content.map((c) => c.signals),
    1,
  );
  const readingPercent =
    totalSignals === 0
      ? 0
      : Math.round((loaderData.overview.readingSignals / totalSignals) * 100);
  const listeningPercent = totalSignals === 0 ? 0 : 100 - readingPercent;
  const peak =
    [...loaderData.rhythm].sort((a, b) => b.signals - a.signals)[0] ?? null;

  return (
    <div className="pf-usage pf-usage-canvas">
      <section className="pf-usage-hero" aria-labelledby="usage-heading">
        <div className="pf-usage-hero__copy">
          <p className="pf-eyebrow">
            <Icon icon={faChartLine} />
            Usage dashboard
          </p>
          <h2 id="usage-heading" className="pf-title pf-title--xs">
            Reading and listening, from now forward.
          </h2>
          <p className="pf-note">
            Country-level activity only. Raw IP addresses and user agents are
            not stored.
          </p>
        </div>
        <div className="pf-usage-hero__pulse" aria-label="Latest activity">
          <Icon icon={faClock} />
          <span>
            {loaderData.overview.lastSeenAt
              ? formatWhen(loaderData.overview.lastSeenAt)
              : "No activity yet"}
          </span>
        </div>
      </section>

      <section className="pf-usage-metrics" aria-label="Usage at a glance">
        <UsageMetric
          icon={faUserGroup}
          label="Active readers"
          value={loaderData.overview.activePeople}
          hint="people with activity"
        />
        <UsageMetric
          icon={faBookOpen}
          label="Reading"
          value={loaderData.overview.readingSignals}
          hint="progress signals"
        />
        <UsageMetric
          icon={faHeadphones}
          label="Listening"
          value={loaderData.overview.listeningSignals}
          hint="playback signals"
        />
        <UsageMetric
          icon={faGlobeAmericas}
          label="Countries"
          value={loaderData.overview.countries}
          hint={topCountry}
        />
        <UsageMetric
          icon={faSignal}
          label="Most used"
          value={loaderData.overview.activeTitles}
          hint={topTitle}
        />
      </section>

      <UsageTabNav
        active={view}
        counts={{
          activity: loaderData.recent.length,
          people: loaderData.overview.activePeople,
          content: loaderData.overview.activeTitles,
          countries: loaderData.overview.countries,
        }}
      />

      {totalSignals === 0 ? (
        <section className="pf-panel pf-usage-empty">
          <Icon icon={faSignal} />
          <h2>No usage has been collected yet.</h2>
          <p className="pf-note">
            The dashboard starts from this release. It will fill as invited
            people read chapters or play episodes.
          </p>
        </section>
      ) : (
        <section className="pf-usage-tabpanel">
          {view === "overview" ? (
            <OverviewTab
              data={loaderData}
              maxContentSignals={maxContentSignals}
              maxCountrySignals={maxCountrySignals}
              readingPercent={readingPercent}
              listeningPercent={listeningPercent}
              peakLabel={peak?.signals ? peak.label : "No peak yet"}
            />
          ) : null}

          {view === "activity" ? (
            <ActivityTab
              data={loaderData}
              readingPercent={readingPercent}
              listeningPercent={listeningPercent}
              peakLabel={peak?.signals ? peak.label : "No peak yet"}
            />
          ) : null}

          {view === "people" ? (
            <PeoplePanel people={loaderData.people} />
          ) : null}
          {view === "content" ? (
            <TopContentPanel
              content={loaderData.content}
              max={maxContentSignals}
            />
          ) : null}
          {view === "countries" ? (
            <CountriesTab
              countries={loaderData.countries}
              max={maxCountrySignals}
            />
          ) : null}
        </section>
      )}
    </div>
  );
}

function OverviewTab({
  data,
  maxContentSignals,
  maxCountrySignals,
  readingPercent,
  listeningPercent,
  peakLabel,
}: {
  data: UsageData;
  maxContentSignals: number;
  maxCountrySignals: number;
  readingPercent: number;
  listeningPercent: number;
  peakLabel: string;
}) {
  return (
    <div className="pf-usage-overview">
      <section className="pf-usage-mosaic" aria-label="Usage overview">
        <ModeSplit
          className="pf-usage-tile pf-usage-tile--split"
          reading={data.overview.readingSignals}
          listening={data.overview.listeningSignals}
          readingPercent={readingPercent}
          listeningPercent={listeningPercent}
        />
        <CountryHeat
          className="pf-usage-tile pf-usage-tile--country"
          countries={data.countries.slice(0, 6)}
          max={maxCountrySignals}
        />
        <RhythmStrip
          className="pf-usage-tile pf-usage-tile--rhythm"
          rhythm={data.rhythm}
          peakLabel={peakLabel}
        />
        <TopContentPanel
          className="pf-usage-tile pf-usage-tile--content"
          content={data.content.slice(0, 5)}
          max={maxContentSignals}
        />
        <RecentActivityPanel
          className="pf-usage-tile pf-usage-tile--recent"
          recent={data.recent.slice(0, 6)}
          compact
          wide={false}
        />
      </section>
    </div>
  );
}

function ActivityTab({
  data,
  readingPercent,
  listeningPercent,
  peakLabel,
}: {
  data: UsageData;
  readingPercent: number;
  listeningPercent: number;
  peakLabel: string;
}) {
  return (
    <div className="pf-usage-grid">
      <section
        className="pf-usage-visuals pf-usage-visuals--duo pf-usage-panel--wide"
        aria-label="Activity rhythm"
      >
        <RhythmStrip rhythm={data.rhythm} peakLabel={peakLabel} />
        <ModeSplit
          reading={data.overview.readingSignals}
          listening={data.overview.listeningSignals}
          readingPercent={readingPercent}
          listeningPercent={listeningPercent}
        />
      </section>
      <RecentActivityPanel recent={data.recent} />
    </div>
  );
}

function CountriesTab({
  countries,
  max,
}: {
  countries: UsageData["countries"];
  max: number;
}) {
  return (
    <div className="pf-usage-grid">
      <section
        className="pf-usage-visuals pf-usage-visuals--single pf-usage-panel--wide"
        aria-label="Country activity"
      >
        <CountryHeat countries={countries} max={max} />
      </section>
      <CountriesPanel countries={countries} max={max} />
    </div>
  );
}

function UsageTabNav({
  active,
  counts,
}: {
  active: UsageView;
  counts: Record<Exclude<UsageView, "overview">, number>;
}) {
  return (
    <nav className="pf-usage-tabs" aria-label="Usage sections">
      {USAGE_TABS.map((tab) => {
        const count = usageTabCount(tab.key, counts);
        return (
          <Link
            key={tab.key}
            to={
              tab.key === "overview"
                ? "/admin/usage"
                : `/admin/usage?view=${tab.key}`
            }
            className={
              active === tab.key
                ? "pf-usage-tab pf-usage-tab--active"
                : "pf-usage-tab"
            }
            aria-current={active === tab.key ? "page" : undefined}
          >
            <span>{tab.label}</span>
            {count === null ? null : (
              <strong className="pf-usage-tab__meta">
                {count.toLocaleString()}
              </strong>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

function RecentActivityPanel({
  recent,
  compact = false,
  wide = true,
  className,
}: {
  recent: UsageData["recent"];
  compact?: boolean;
  wide?: boolean;
  className?: string;
}) {
  return (
    <section
      className={
        wide
          ? "pf-panel pf-usage-panel pf-usage-panel--wide " + (className ?? "")
          : "pf-panel pf-usage-panel " + (className ?? "")
      }
    >
      <div className="pf-panel__head">
        <div>
          <h2>Recent Activity</h2>
          <p>
            {compact
              ? "A quick pulse of the latest signals."
              : "Latest reading and listening signals."}
          </p>
        </div>
      </div>
      <div
        className={
          compact
            ? "pf-activity-list pf-activity-list--compact"
            : "pf-activity-list"
        }
      >
        {recent.map((event) => (
          <article
            key={`${event.email}-${event.slug}-${event.kind}-${event.targetKey}-${event.countryCode}`}
            className="pf-activity"
          >
            <div
              className={
                event.kind === "listen"
                  ? "pf-activity__icon pf-activity__icon--listen"
                  : "pf-activity__icon pf-activity__icon--read"
              }
            >
              <Icon
                icon={event.kind === "listen" ? faHeadphones : faBookOpen}
              />
            </div>
            <div className="pf-activity__body">
              <div className="pf-activity__line">
                <strong>{event.name}</strong>
                <span>{event.kind === "listen" ? "listened to" : "read"}</span>
                <strong>{event.title}</strong>
              </div>
              <div className="pf-activity__meta">
                <span>
                  {event.targetTitle ??
                    targetFallback(event.kind, event.targetKey)}
                </span>
                <span>
                  <Icon icon={faLocationDot} /> {event.countryName}
                </span>
                <span>{formatWhen(event.lastSeenAt)}</span>
                <span>{event.signalCount.toLocaleString()} signals</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function CountriesPanel({
  countries,
  max,
}: {
  countries: UsageData["countries"];
  max: number;
}) {
  return (
    <section className="pf-panel pf-usage-panel">
      <div className="pf-panel__head">
        <div>
          <h2>Countries</h2>
          <p>Where activity is coming from.</p>
        </div>
      </div>
      <div className="pf-ranked">
        {countries.map((country) => (
          <RankedBar
            key={country.code}
            label={country.name}
            meta={`${country.people} ${country.people === 1 ? "person" : "people"}`}
            value={country.signals}
            max={max}
          />
        ))}
      </div>
    </section>
  );
}

function TopContentPanel({
  content,
  max,
  className,
}: {
  content: UsageData["content"];
  max: number;
  className?: string;
}) {
  return (
    <section
      className={
        className
          ? "pf-panel pf-usage-panel " + className
          : "pf-panel pf-usage-panel"
      }
    >
      <div className="pf-panel__head">
        <div>
          <h2>Top Content</h2>
          <p>Books and sessions people return to.</p>
        </div>
      </div>
      <div className="pf-ranked">
        {content.map((item) => (
          <RankedBar
            key={item.slug}
            label={item.title}
            meta={`${item.people} ${item.people === 1 ? "person" : "people"} · ${item.bucket}`}
            value={item.signals}
            max={max}
          />
        ))}
      </div>
    </section>
  );
}

function PeoplePanel({ people }: { people: UsageData["people"] }) {
  return (
    <section className="pf-panel pf-usage-panel pf-usage-panel--wide">
      <div className="pf-panel__head">
        <div>
          <h2>People</h2>
          <p>Who has been active most recently.</p>
        </div>
      </div>
      <div className="pf-usage-table-wrap">
        <table className="pf-usage-table">
          <thead>
            <tr>
              <th>Person</th>
              <th>Countries</th>
              <th>Titles</th>
              <th>Reading</th>
              <th>Listening</th>
              <th>Last active</th>
            </tr>
          </thead>
          <tbody>
            {people.map((person) => (
              <tr key={person.email}>
                <td>
                  <strong>{person.name}</strong>
                  <span>{person.email}</span>
                </td>
                <td>{person.countries.join(", ") || "Unknown"}</td>
                <td>{person.titles}</td>
                <td>{person.readingSignals.toLocaleString()}</td>
                <td>{person.listeningSignals.toLocaleString()}</td>
                <td>{formatWhen(person.lastSeenAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ModeSplit({
  className,
  reading,
  listening,
  readingPercent,
  listeningPercent,
}: {
  className?: string;
  reading: number;
  listening: number;
  readingPercent: number;
  listeningPercent: number;
}) {
  const background =
    reading + listening === 0
      ? undefined
      : `conic-gradient(var(--l-accent) 0 ${readingPercent}%, var(--l-success) ${readingPercent}% 100%)`;

  return (
    <article
      className={
        className
          ? "pf-panel pf-usage-visual pf-usage-split " + className
          : "pf-panel pf-usage-visual pf-usage-split"
      }
    >
      <div className="pf-usage-visual__head">
        <span>
          <Icon icon={faChartPie} />
        </span>
        <div>
          <h2>Read vs Listen</h2>
          <p>How people are using the Library.</p>
        </div>
      </div>
      <div className="pf-donut-wrap">
        <div
          className="pf-donut"
          style={{ background }}
          aria-label={`${readingPercent}% reading, ${listeningPercent}% listening`}
        >
          <span>{readingPercent}%</span>
          <small>reading</small>
        </div>
        <div className="pf-donut-legend">
          <VisualLegend
            icon={faBookOpen}
            label="Reading"
            value={reading}
            percent={readingPercent}
            tone="read"
          />
          <VisualLegend
            icon={faHeadphones}
            label="Listening"
            value={listening}
            percent={listeningPercent}
            tone="listen"
          />
        </div>
      </div>
    </article>
  );
}

function CountryHeat({
  className,
  countries,
  max,
}: {
  className?: string;
  countries: { code: string; name: string; people: number; signals: number }[];
  max: number;
}) {
  return (
    <article
      className={
        className
          ? "pf-panel pf-usage-visual pf-country-heat " + className
          : "pf-panel pf-usage-visual pf-country-heat"
      }
    >
      <div className="pf-usage-visual__head">
        <span>
          <Icon icon={faMapLocationDot} />
        </span>
        <div>
          <h2>Country Heat</h2>
          <p>Where the strongest activity is.</p>
        </div>
      </div>
      <div className="pf-country-cloud">
        {countries.map((country) => {
          const level = Math.max(18, Math.round((country.signals / max) * 100));
          return (
            <div key={country.code} className="pf-country-card">
              <div className="pf-country-card__code">{country.code}</div>
              <div className="pf-country-card__body">
                <strong>{country.name}</strong>
                <span>
                  {country.people} {country.people === 1 ? "person" : "people"}
                </span>
              </div>
              <div className="pf-country-card__meter" aria-hidden="true">
                <span style={{ width: `${level}%` }} />
              </div>
              <em>{country.signals.toLocaleString()}</em>
            </div>
          );
        })}
      </div>
    </article>
  );
}

function RhythmStrip({
  className,
  rhythm,
  peakLabel,
}: {
  className?: string;
  rhythm: { hour: number; label: string; signals: number }[];
  peakLabel: string;
}) {
  const max = Math.max(...rhythm.map((h) => h.signals), 1);

  return (
    <article
      className={
        className
          ? "pf-panel pf-usage-visual pf-rhythm " + className
          : "pf-panel pf-usage-visual pf-rhythm"
      }
    >
      <div className="pf-usage-visual__head">
        <span>
          <Icon icon={faWaveSquare} />
        </span>
        <div>
          <h2>Daily Rhythm</h2>
          <p>Peak signal window: {peakLabel}.</p>
        </div>
      </div>
      <div className="pf-rhythm-bars" aria-label="Activity by hour">
        {rhythm.map((hour) => {
          const height = `${Math.max(8, Math.round((hour.signals / max) * 100))}%`;
          return (
            <span
              key={hour.hour}
              title={`${hour.label}: ${hour.signals} signals`}
            >
              <i style={{ height }} />
            </span>
          );
        })}
      </div>
      <div className="pf-rhythm-axis" aria-hidden="true">
        <span>12 AM</span>
        <span>6 AM</span>
        <span>12 PM</span>
        <span>6 PM</span>
      </div>
    </article>
  );
}

function VisualLegend({
  icon,
  label,
  value,
  percent,
  tone,
}: {
  icon: IconDefinition;
  label: string;
  value: number;
  percent: number;
  tone: "read" | "listen";
}) {
  return (
    <div
      className={
        tone === "listen"
          ? "pf-visual-legend pf-visual-legend--listen"
          : "pf-visual-legend pf-visual-legend--read"
      }
    >
      <Icon icon={icon} />
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
      <em>{percent}%</em>
    </div>
  );
}

function UsageMetric({
  icon,
  label,
  value,
  hint,
}: {
  icon: IconDefinition;
  label: string;
  value: number;
  hint: string;
}) {
  return (
    <article className="pf-usage-metric">
      <span className="pf-usage-metric__icon">
        <Icon icon={icon} />
      </span>
      <span className="pf-usage-metric__label">{label}</span>
      <strong>{value.toLocaleString()}</strong>
      <span className="pf-usage-metric__hint">{hint}</span>
    </article>
  );
}

function RankedBar({
  label,
  meta,
  value,
  max,
}: {
  label: string;
  meta: string;
  value: number;
  max: number;
}) {
  const width = `${Math.max(6, Math.round((value / max) * 100))}%`;

  return (
    <div className="pf-ranked__item">
      <div className="pf-ranked__top">
        <strong>{label}</strong>
        <span>{value.toLocaleString()}</span>
      </div>
      <div className="pf-ranked__track" aria-hidden="true">
        <span style={{ width }} />
      </div>
      <p>{meta}</p>
    </div>
  );
}

function usageView(view: string | null): UsageView {
  return USAGE_TABS.some((tab) => tab.key === view)
    ? (view as UsageView)
    : "overview";
}

function usageTabCount(
  view: UsageView,
  counts: Record<Exclude<UsageView, "overview">, number>,
): number | null {
  switch (view) {
    case "activity":
      return counts.activity;
    case "people":
      return counts.people;
    case "content":
      return counts.content;
    case "countries":
      return counts.countries;
    case "overview":
      return null;
  }
}

function targetFallback(kind: UsageKind, key: string): string {
  return kind === "listen" ? `Episode ${key}` : key.replace(/-/g, " ");
}

function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime())) return "Unknown";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
    timeZoneName: "short",
  }).format(date);
}
