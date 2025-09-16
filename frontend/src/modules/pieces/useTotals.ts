import { useMemo } from "react";
import { isValidAmount, toCents } from "../utils/amount";
import type { TotalsInfo } from "./types";

export function useTotals(rows: { debit: string; credit: string; markedDeleted?: boolean }[]): TotalsInfo {

    return useMemo(() => {
        let d = 0, c = 0, hasErrors = false, bothSides = false;

        for (const r of rows) {
            if (r.markedDeleted) continue;

            const debit = toCents(r.debit);
            const credit = toCents(r.credit);

            const hasD = debit !== 0 && isValidAmount(r.debit);
            const hasC = credit !== 0 && isValidAmount(r.credit);

            if (debit !== 0 && !hasD) hasErrors = true;
            if (credit !== 0 && !hasC) hasErrors = true;
            if (hasD && hasC) bothSides = true;


            if (hasD) d += debit;
            if (hasC) c += credit;
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
