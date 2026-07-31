// Status hexes are fixed regardless of theme (see dataviz palette.md) — used
// here only as a decorative accent bar, never as the sole carrier of meaning;
// the label and value text next to each tile say what the number means.
const GOOD = "#0ca30c";
// The palette's own #fab219 clears only 1.79:1 on the light surface (documented
// in palette.md) -- too low for a UI-component accent (WCAG 1.4.11 wants 3:1).
// Stepped down in value, same hue, until it cleared 3:1 on both surfaces.
const WARNING = "#bf7900";
const CRITICAL = "#d03b3b";

function StatTile({ label, value, caption, accent }) {
  return (
    <div className="kpi-tile" style={{ "--tile-accent": accent }}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {caption ? <div className="kpi-caption">{caption}</div> : null}
    </div>
  );
}

function findRate(metrics, name) {
  return metrics.find((m) => m.metric === name)?.rate ?? 0;
}

function findItem(items, label) {
  return items.find((i) => i.label === label);
}

/** Headline numbers row -- the "handful of KPIs" the dashboard leads with,
 * pulled from data already on the page rather than a separate request. */
export function KpiRow({ effectiveness, risk, intimation, cumulative, tokens }) {
  const highRisk = findItem(risk.items, "High Risk");
  const gap = findItem(intimation.items, "No Proper Intimation");

  const tiles = [
    {
      label: "Processed rows",
      value: effectiveness.processed_rows.toLocaleString(),
      caption: "in current filter",
      accent: tokens.volume,
    },
    {
      label: "Valid discussions",
      value: effectiveness.valid_discussions.toLocaleString(),
      caption: `${findRate(effectiveness.metrics, "Valid Discussions").toFixed(1)}% of processed`,
      accent: tokens.volume,
    },
    {
      label: "Positive commitment",
      value: `${findRate(effectiveness.metrics, "Positive Commitment").toFixed(1)}%`,
      caption: `${effectiveness.positive_commitment.toLocaleString()} calls`,
      accent: GOOD,
    },
    {
      label: "High risk cases",
      value: (highRisk?.count ?? 0).toLocaleString(),
      caption: highRisk ? `${highRisk.percentage.toFixed(1)}% of valid` : "—",
      accent: CRITICAL,
    },
    {
      label: "Intimation gap",
      value: (gap?.count ?? 0).toLocaleString(),
      caption: gap ? `${gap.percentage.toFixed(1)}% of valid` : "—",
      accent: WARNING,
    },
    {
      label: "This month",
      value: cumulative.total.toLocaleString(),
      caption: "cumulative calls",
      accent: tokens.cumulative,
    },
  ];

  return (
    <div className="kpi-row">
      {tiles.map((tile) => (
        <StatTile key={tile.label} {...tile} />
      ))}
    </div>
  );
}
