/** Section wrapper: numbered band matching the dashboard spec. */
export function Section({ num, title, children }) {
  return (
    <section className="section">
      <header>
        <span className="num">{num}</span>
        {title}
      </header>
      <div className="section-body">{children}</div>
    </section>
  );
}

const pct = (value) => `${value.toFixed(1)}%`;

/** Label / calls / % table -- the table-view twin every chart needs.
 * `maxHeight`, when given, turns on a scrolling body with a sticky header --
 * for tables with more rows than comfortably fit in a card. */
export function BreakdownTable({
  items,
  total,
  labelHeader = "Category",
  colors,
  showTotal = true,
  maxHeight,
}) {
  return (
    <div
      className={`table-wrap${maxHeight ? " scroll" : ""}`}
      style={maxHeight ? { "--th-max-height": `${maxHeight}px` } : undefined}
    >
      <table>
        <thead>
          <tr>
            <th>{labelHeader}</th>
            <th className="num">Calls</th>
            <th className="num">%</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={item.label}>
              <td>
                {colors ? (
                  <i className="swatch" style={{ background: colors[index] }} />
                ) : null}
                {item.label}
              </td>
              <td className="num">{item.count.toLocaleString()}</td>
              <td className="num">{pct(item.percentage)}</td>
            </tr>
          ))}
          {showTotal ? (
            <tr className="total">
              <td>Total</td>
              <td className="num">{total.toLocaleString()}</td>
              <td className="num">100.0%</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

/** Section 5: the effectiveness funnel, with each rate's basis made explicit. */
export function EffectivenessTable({ data }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th className="num">Calls</th>
            <th className="num">% / Rate</th>
            <th>Basis</th>
          </tr>
        </thead>
        <tbody>
          {data.metrics.map((metric) => (
            <tr key={metric.metric}>
              <td>{metric.metric}</td>
              <td className="num">{metric.calls.toLocaleString()}</td>
              <td className="num">{pct(metric.rate)}</td>
              <td style={{ color: "var(--text-secondary)", fontSize: 12 }}>
                of {metric.basis === "valid" ? "valid discussions" : "processed calls"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Section 3: category areas with their leading sub-reason themes. */
export function MdInsightsTable({ data, maxHeight }) {
  return (
    <div
      className={`table-wrap${maxHeight ? " scroll" : ""}`}
      style={maxHeight ? { "--th-max-height": `${maxHeight}px` } : undefined}
    >
      <table>
        <thead>
          <tr>
            <th>Area</th>
            <th className="num">Calls</th>
            <th className="num">%</th>
          </tr>
        </thead>
        <tbody>
          {data.areas.map((area) => (
            <tr key={area.area}>
              <td style={{ whiteSpace: "nowrap" }}>{area.area}</td>
              <td className="num">{area.calls.toLocaleString()}</td>
              <td className="num">{pct(area.percentage)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Table twin for the two time-series charts, so no value is tooltip-gated. */
export function SeriesTable({ rows, firstHeader, valueHeader }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{firstHeader}</th>
            <th className="num">{valueHeader}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <td>{row.key}</td>
              <td className="num">{row.value.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
