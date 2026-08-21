// Hex mirrors of the Tailwind brand palette (src/index.css @theme) — recharts
// needs real color values, not utility class names.
export const COLORS = {
  brand: "#465fff",
  brandLight: "#7592ff",
  success: "#12b76a",
  warning: "#f79009",
  error: "#f04438",
  gray: "#d0d5dd",
};

export const CATEGORY_HEX: Record<string, string> = {
  productive: COLORS.success,
  neutral: COLORS.brandLight,
  distraction: COLORS.error,
  uncategorised: COLORS.gray,
};
