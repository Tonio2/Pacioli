export const cleanAmount = (s: unknown) =>
  String(s ?? "")
    .replace(/\u00A0/g, " ")
    .replace(/\s+/g, "")
    .replace(",", ".");

export const isValidAmount = (s: string) => {
  if (s == null || s === "") return false;
  const t = cleanAmount(s);
  return /^-?\d+(\.\d+)?$/.test(t);
};

export const toNumber = (s: string) => {
  const n = parseFloat(cleanAmount(s));
  return Number.isFinite(n) ? n : 0;
};
