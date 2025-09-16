const fmtEUR = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' });
const fmtFR = new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
});

export const fmtCents = (cents: number | null | undefined) => {
    if (cents == null) return "—";
    return fmtEUR.format(cents / 100);
};

export const centsToInput = (cents: number | null | undefined): string => {
    if (cents == null) return "";
    return fmtFR.format(cents / 100)
}

export const cleanAmount = (s: unknown) =>
    String(s ?? "")
        .replace(/\u00A0/g, " ")   // nbsp -> espace normal
        .replace(/\s+/g, "")       // supprime espaces
        .replace(",", ".");        // virgule -> point

/** Vérifie "nombre décimal" simple (avec - optionnel) */
export const isValidAmount = (s: string) => {
    if (s == null || s === "") return false;
    const t = cleanAmount(s);
    return /^-?\d+(\.\d{0,})?$/.test(t);
};

/** Parse en centimes (number), arrondi bancaire classique */
export const toCents = (s: string): number => {
    const t = cleanAmount(s);
    const n = parseFloat(t);
    if (!Number.isFinite(n)) return 0;
    // évite erreurs de flottants: on arrondit au centime
    return Math.round(n * 100);
};
