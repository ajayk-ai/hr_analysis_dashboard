import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchDashboard, fetchFilterOptions } from "./api";
import { CumulativeArea, MonthlyBars, ShareBar } from "./components/charts";
import {
  BreakdownTable,
  EffectivenessTable,
  MdInsightsTable,
  Section,
  SeriesTable,
} from "./components/tables";
import { ordinalSteps, themes } from "./theme";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function prettyMonth(month) {
  if (!month) return "";
  return `${MONTH_NAMES[Number(month.slice(5, 7)) - 1]} ${month.slice(0, 4)}`;
}

/** Months between the data's first and last, newest first, for the filter. */
function monthOptions(min, max) {
  if (!min || !max) return [];
  const out = [];
  let year = Number(max.slice(0, 4));
  let mon = Number(max.slice(5, 7));
  const minYear = Number(min.slice(0, 4));
  const minMon = Number(min.slice(5, 7));
  while (year > minYear || (year === minYear && mon >= minMon)) {
    out.push(`${year}-${String(mon).padStart(2, "0")}`);
    mon -= 1;
    if (mon === 0) {
      mon = 12;
      year -= 1;
    }
  }
  return out;
}

function useTheme() {
  const [mode, setMode] = useState(
    () =>
      document.documentElement.dataset.theme ||
      (window.matchMedia?.("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"),
  );
  useEffect(() => {
    document.documentElement.dataset.theme = mode;
  }, [mode]);
  return [mode, setMode];
}

export default function App() {
  const [mode, setMode] = useTheme();
  const tokens = themes[mode] ?? themes.light;

  const [options, setOptions] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [refetching, setRefetching] = useState(false);
  const [showTables, setShowTables] = useState(false);

  const [month, setMonth] = useState("");
  const [category, setCategory] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [scope, setScope] = useState("valid_only");

  const params = useMemo(
    () => ({
      month: month || undefined,
      category: category ? [category] : undefined,
      risk_level: riskLevel ? [riskLevel] : undefined,
      scope,
    }),
    [month, category, riskLevel, scope],
  );

  // Guards against an out-of-order response overwriting a newer one.
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const id = ++requestId.current;
    setRefetching(true);
    try {
      const payload = await fetchDashboard(params);
      if (id === requestId.current) {
        setData(payload);
        setError(null);
      }
    } catch (err) {
      if (id === requestId.current) setError(err.message);
    } finally {
      if (id === requestId.current) setRefetching(false);
    }
  }, [params]);

  useEffect(() => {
    fetchFilterOptions()
      .then(setOptions)
      .catch(() => setOptions(null));
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const months = useMemo(
    () => monthOptions(options?.date_min, options?.date_max),
    [options],
  );

  if (error && !data) {
    return (
      <div className="page">
        <div className="notice error">
          Could not reach the API: {error}. Start it with{" "}
          <code>uv run uvicorn backend.api.main:app --reload</code>.
        </div>
      </div>
    );
  }
  if (!data) return <div className="state">Loading dashboard…</div>;

  const {
    effectiveness,
    monthly_valid_discussions: monthly,
    current_month_cumulative: cumulative,
    category_trends: trends,
    md_insights: insights,
    commitment,
    sub_reasons: subReasons,
    intimation_compliance: intimation,
    risk_analysis: risk,
  } = data;

  const scopeLabel =
    scope === "valid_only" ? "valid discussions" : "all processed rows";
  const commitmentColors = ordinalSteps(tokens, commitment.items.length);
  // Risk is ordered low -> high, so the ramp runs with it.
  const riskColors = ordinalSteps(tokens, risk.items.length);

  return (
    <div className="page">
      <header className="masthead">
        <div>
          <h1>HR Absentee Follow-up Call AI Analytics</h1>
          <p className="sub">
            {prettyMonth(data.generated_for_month)} · {scopeLabel} ·{" "}
            {effectiveness.valid_discussions.toLocaleString()} of{" "}
            {effectiveness.processed_rows.toLocaleString()} processed rows
          </p>
        </div>
        <div className="masthead-actions">
          <button className="ghost" onClick={() => setShowTables((v) => !v)}>
            {showTables ? "Hide data tables" : "Show data tables"}
          </button>
          <button
            className="ghost"
            onClick={() => setMode(mode === "dark" ? "light" : "dark")}
          >
            {mode === "dark" ? "Light mode" : "Dark mode"}
          </button>
        </div>
      </header>

      {/* One filter row above everything it scopes. */}
      <div className="filters">
        <div className="field">
          <label htmlFor="f-month">Month</label>
          <select
            id="f-month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
          >
            <option value="">All months</option>
            {months.map((m) => (
              <option key={m} value={m}>
                {prettyMonth(m)}
              </option>
            ))}
          </select>
        </div>
        <div className="field" style={{ minWidth: 240 }}>
          <label htmlFor="f-category">Reason category</label>
          <select
            id="f-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">All categories</option>
            {(options?.categories ?? []).map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-risk">Risk level</label>
          <select
            id="f-risk"
            value={riskLevel}
            onChange={(e) => setRiskLevel(e.target.value)}
          >
            <option value="">All risk levels</option>
            {(options?.risk_levels ?? []).map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-scope">Scope</label>
          <select
            id="f-scope"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
          >
            <option value="valid_only">Valid discussions only</option>
            <option value="all">All processed rows</option>
          </select>
        </div>
        <div className="filters-spacer" />
        <button
          className="ghost"
          onClick={() => {
            setMonth("");
            setCategory("");
            setRiskLevel("");
            setScope("valid_only");
          }}
        >
          Reset
        </button>
      </div>

      <div className={refetching ? "refetching" : undefined}>
        <Section num="1" title="Six month trend analysis">
          <div className="grid-2">
            <div className="card">
              <h3>Valid discussions by month</h3>
              <p className="caption">
                Rolling six months ending {prettyMonth(monthly.anchor_month)}.
              </p>
              <MonthlyBars data={monthly.points} tokens={tokens} />
              {showTables ? (
                <SeriesTable
                  firstHeader="Month"
                  valueHeader="Calls"
                  rows={monthly.points.map((p) => ({
                    key: `${p.label} ${p.month.slice(0, 4)}`,
                    value: p.calls,
                  }))}
                />
              ) : null}
            </div>
            <div className="card">
              <h3>
                {prettyMonth(cumulative.month)} cumulative —{" "}
                {cumulative.total.toLocaleString()} calls
              </h3>
              <p className="caption">
                Running total by day of month, shown separately from the
                six-month bars.
              </p>
              <CumulativeArea data={cumulative.points} tokens={tokens} />
              {showTables ? (
                <SeriesTable
                  firstHeader="Day"
                  valueHeader="Cumulative"
                  rows={cumulative.points.map((p) => ({
                    key: `Day ${p.day}`,
                    value: p.cumulative,
                  }))}
                />
              ) : null}
            </div>
          </div>
        </Section>

        <Section num="2" title="Absentee reason analytics">
          <div className="grid-3">
            {trends.categories.map((cat) => (
              <div className="card" key={cat.category}>
                <h3>{cat.category}</h3>
                <p className="caption">
                  {prettyMonth(trends.anchor_month)}:{" "}
                  {cat.current_month_calls.toLocaleString()} (
                  {cat.current_month_percentage.toFixed(1)}%)
                </p>
                <MonthlyBars
                  data={cat.monthly}
                  tokens={tokens}
                  height={132}
                  compact
                />
                <CumulativeArea
                  data={cat.cumulative}
                  tokens={tokens}
                  height={132}
                  compact
                />
                {showTables ? (
                  <SeriesTable
                    firstHeader="Month"
                    valueHeader="Calls"
                    rows={cat.monthly.map((p) => ({
                      key: p.label,
                      value: p.calls,
                    }))}
                  />
                ) : null}
              </div>
            ))}
          </div>
          <p className="notice">
            Blue columns are calls per month; the orange line is the cumulative
            run through {prettyMonth(trends.anchor_month)}. Two measures, two
            plots — deliberately not a dual axis.
          </p>
        </Section>

        <div className="grid-wide-first">
          <Section num="3" title="Critical insights to MD">
            <MdInsightsTable data={insights} />
            <p className="notice">
              Break-ups group the free-text AI sub-reason into keyword themes and
              show each area's leading themes, so they need not sum to the area
              total. The risk row overlaps the categories above it.
            </p>
          </Section>

          <Section num="4" title="Return commitment tracking">
            <ShareBar
              items={commitment.items}
              colors={commitmentColors}
              tokens={tokens}
            />
            <BreakdownTable
              items={commitment.items}
              total={commitment.total}
              labelHeader="Status"
              colors={commitmentColors}
            />
          </Section>

          <Section num="5" title="HR call effectiveness metrics">
            <EffectivenessTable data={effectiveness} />
          </Section>
        </div>

        <div className="grid-wide-first">
          <Section num="6" title="Reason-wise detailed breakdown">
            <BreakdownTable
              items={subReasons.items}
              total={subReasons.total}
              labelHeader="Sub reason theme"
            />
          </Section>

          <Section num="7" title="Intimation compliance">
            <BreakdownTable
              items={intimation.items}
              total={intimation.total}
              labelHeader="Compliance level"
            />
          </Section>

          <Section num="8" title="Attrition risk analysis">
            <ShareBar items={risk.items} colors={riskColors} tokens={tokens} />
            <BreakdownTable
              items={risk.items}
              total={risk.total}
              labelHeader="Risk level"
              colors={riskColors}
            />
          </Section>
        </div>

        <p className="notice">
          Department and Location filters from the original spec are omitted:
          <code> preprocess_call_log </code> carries no such columns (emp_code,
          emp_tags and crm_status are null in every row). Percentages are shares
          of {scopeLabel}.
        </p>
      </div>
    </div>
  );
}
