import { useMemo } from "react";
import { isValidAmount, toNumber } from "./amount";
import type { TotalsInfo } from "./types";

export function useTotals(rows: { debit: string; credit: string; markedDeleted?: boolean }[]): TotalsInfo {
    const cents = (s: string) => Math.round(toNumber(s) * 100);

    return useMemo(() => {
        let d = 0, c = 0, hasErrors = false, bothSides = false;

        for (const r of rows) {
            if (r.markedDeleted) continue;

            const hasD = r.debit !== "0" && isValidAmount(r.debit);
            const hasC = r.credit !== "0" && isValidAmount(r.credit);

            if (r.debit !== "0" && !hasD) hasErrors = true;
            if (r.credit !== "0" && !hasC) hasErrors = true;
            if (hasD && hasC) bothSides = true;


            if (hasD) d += cents(r.debit);
            if (hasC) c += cents(r.credit);
        }

        const diffCents = d - c;
        return {
            debit: d / 100,
            credit: c / 100,
            diff: diffCents / 100,
            isBalanced: diffCents === 0,
            hasAmountErrors: hasErrors,
            bothSidesFilled: bothSides,
        };
    }, [rows]);
}
