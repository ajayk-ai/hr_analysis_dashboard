/**
 * Chart tokens. Every colour here comes from the validated palette:
 *  - volume marks use categorical slot 1 (blue), cumulative uses slot 2 (orange);
 *    they never share a plot, so no dual-axis and no adjacent-pair risk.
 *  - ordered scales (risk, commitment) use the ordinal blue ramp rather than
 *    status hues, whose light-surface yellow fails the lightness band.
 *
 * Ordinal direction is by contrast, not hex: the highest step is the most
 * visible against its own surface (darkest on light, brightest on dark).
 */

const LIGHT = {
  surface: "#fcfcfb",
  plane: "#f9f9f7",
  textPrimary: "#0b0b0b",
  textSecondary: "#52514e",
  textMuted: "#898781",
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  border: "rgba(11,11,11,0.10)",
  volume: "#2a78d6",
  cumulative: "#eb6834",
  // Validated: ordinal ramp, light mode, light end no lighter than step 250.
  ordinal: ["#86b6ef", "#3987e5", "#1c5cab"],
  neutral: "#c3c2b7",
};

const DARK = {
  surface: "#1a1a19",
  plane: "#0d0d0d",
  textPrimary: "#ffffff",
  textSecondary: "#c3c2b7",
  textMuted: "#898781",
  grid: "#2c2c2a",
  axis: "#383835",
  border: "rgba(255,255,255,0.10)",
  volume: "#3987e5",
  cumulative: "#d95926",
  // Validated: ordinal ramp, dark mode, dark end no darker than step 600.
  ordinal: ["#184f95", "#3987e5", "#9ec5f4"],
  neutral: "#52514e",
};

export const themes = { light: LIGHT, dark: DARK };

/** Steps for an ordered scale of `n` classes, plus neutral for "unspecified". */
export function ordinalSteps(tokens, n) {
  const ramp = tokens.ordinal;
  if (n <= 1) return [ramp[ramp.length - 1]];
  if (n === 2) return [ramp[0], ramp[2]];
  if (n === 3) return ramp;
  // A 4th class is always the "Unspecified" tail -- neutral, not a new step.
  return [...ramp, tokens.neutral];
}
