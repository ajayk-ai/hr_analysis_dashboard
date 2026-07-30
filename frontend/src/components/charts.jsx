import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/** Mark specs shared by every chart (see dataviz marks-and-anatomy). */
const BAR_MAX = 24;
const BAR_RADIUS = [4, 4, 0, 0]; // rounded data-end, square at the baseline
const LINE_WIDTH = 2;
const AREA_OPACITY = 0.1;
const TICK = 11;

/**
 * Y-axis ticks on clean round numbers. Recharts' default divides the domain
 * into equal parts, which yields ticks like 7/14/21/28 on small ranges.
 */
function niceTicks(max, count = 4) {
  if (!max || max <= 0) return [0];
  const rough = max / count;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step =
    [1, 2, 2.5, 5, 10].find((m) => magnitude * m >= rough) * magnitude;
  const ticks = [];
  for (let value = 0; value <= max + step / 2; value += step) {
    ticks.push(Math.round(value));
  }
  return ticks;
}

function ChartTooltip({ active, payload, label, unit }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="tooltip">
      <div className="tt-label">{label}</div>
      <div className="tt-value">
        {payload[0].value.toLocaleString()} {unit}
      </div>
    </div>
  );
}

/**
 * Monthly volume columns. Every column carries its value on the cap, so the
 * y-axis and gridlines are dropped rather than repeating the same numbers.
 */
export function MonthlyBars({ data, tokens, height = 190, compact = false }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 20, right: 8, bottom: 4, left: 8 }}>
        <XAxis
          dataKey="label"
          tick={{ fill: tokens.textMuted, fontSize: compact ? 10 : TICK }}
          axisLine={{ stroke: tokens.axis }}
          tickLine={false}
        />
        {/* Hidden axis still sets the scale; values live on the caps. */}
        <YAxis hide domain={[0, (max) => Math.ceil(max * 1.18) || 1]} />
        <Tooltip
          content={<ChartTooltip unit="calls" />}
          cursor={{ fill: tokens.grid, opacity: 0.5 }}
        />
        <Bar
          dataKey="calls"
          fill={tokens.volume}
          maxBarSize={compact ? 18 : BAR_MAX}
          radius={BAR_RADIUS}
          isAnimationActive={false}
        >
          <LabelList
            dataKey="calls"
            position="top"
            fill={tokens.textSecondary}
            fontSize={compact ? 10 : TICK}
            fontWeight={650}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * Cumulative progress through the current month. Single series, so no legend --
 * the card title names it. Only the endpoint is direct-labelled.
 */
export function CumulativeArea({ data, tokens, height = 190, compact = false }) {
  const peak = data.length ? data[data.length - 1].cumulative : 0;
  const ticks = niceTicks(peak);
  const domainMax = ticks[ticks.length - 1] || 1;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 20, right: 34, bottom: 4, left: 8 }}>
        <CartesianGrid stroke={tokens.grid} strokeWidth={1} vertical={false} />
        <XAxis
          dataKey="day"
          tick={{ fill: tokens.textMuted, fontSize: compact ? 10 : TICK }}
          axisLine={{ stroke: tokens.axis }}
          tickLine={false}
          interval={compact ? 9 : 4}
        />
        <YAxis
          tick={{ fill: tokens.textMuted, fontSize: compact ? 10 : TICK }}
          axisLine={false}
          tickLine={false}
          width={compact ? 26 : 34}
          domain={[0, domainMax]}
          ticks={ticks}
          allowDecimals={false}
        />
        <Tooltip
          content={<ChartTooltip unit="calls to date" />}
          cursor={{ stroke: tokens.axis, strokeWidth: 1 }}
          labelFormatter={(day) => `Day ${day}`}
        />
        <Area
          type="monotone"
          dataKey="cumulative"
          stroke={tokens.cumulative}
          strokeWidth={LINE_WIDTH}
          fill={tokens.cumulative}
          fillOpacity={AREA_OPACITY}
          // A dot per day would be 31 marks; the endpoint is the only one that reads.
          dot={false}
          activeDot={{ r: 4, strokeWidth: 2, stroke: tokens.surface }}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/**
 * Ink for a label sitting inside a colored fill: white or near-black, whichever
 * has the better WCAG contrast against that fill. A fixed white would drop to
 * ~1.9:1 on the light end of the ordinal ramp.
 */
function readableInk(hex) {
  const channel = (offset) => parseInt(hex.slice(offset, offset + 2), 16) / 255;
  const linear = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const luminance =
    0.2126 * linear(channel(1)) +
    0.7152 * linear(channel(3)) +
    0.0722 * linear(channel(5));
  const onWhite = 1.05 / (luminance + 0.05);
  const onBlack = (luminance + 0.05) / 0.05;
  return onWhite >= onBlack ? "#ffffff" : "#0b0b0b";
}

/** Part-to-whole as a segmented bar: safe when shares are near-equal, unlike a pie. */
export function ShareBar({ items, colors, tokens }) {
  const total = items.reduce((sum, item) => sum + item.count, 0) || 1;
  return (
    <>
      <div
        className="sharebar"
        role="img"
        aria-label={items
          .map((item) => `${item.label} ${item.percentage}%`)
          .join(", ")}
      >
        {items.map((item, index) => {
          const share = (item.count / total) * 100;
          // Only label in-segment when the text comfortably fits.
          const fits = share >= 11;
          return (
            <span
              key={item.label}
              style={{
                width: `${share}%`,
                background: colors[index],
                color: readableInk(colors[index]),
              }}
              title={`${item.label}: ${item.count} (${item.percentage.toFixed(1)}%)`}
            >
              {fits ? `${item.percentage.toFixed(1)}%` : ""}
            </span>
          );
        })}
      </div>
      <div className="legend">
        {items.map((item, index) => (
          <span className="item" key={item.label}>
            <i className="swatch" style={{ background: colors[index] }} />
            {item.label}
          </span>
        ))}
      </div>
    </>
  );
}
