// src/pages/NewPiecePage.tsx
import { useCallback, useEffect, useReducer, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";

import { useTotals } from "../modules/pieces/useTotals";
import { rowsReducer, makeRow } from "../modules/pieces/rowsReducer";
import { useAccountSuggest } from "../modules/pieces/useAccountSuggest";
import { toCents } from "../modules/utils/amount";
import PieceRowsTable from "../components/PieceRowsTable";

export default function NewPiecePage() {
    const { clientId, exerciceId } = useApp();
    const qc = useQueryClient();

    const [journal, setJournal] = useState("");
    const [pieceRef, setPieceRef] = useState("");
    const [rows, dispatch] = useReducer(rowsReducer, [makeRow()]);
    const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);

    const { itemsByUid, onChange: onAccSuggest, clear: clearSuggest } = useAccountSuggest(
        clientId as number | undefined
    );

    const { refetch: refetchNext } = useQuery({
        queryKey: ["next_ref", exerciceId, journal],
        queryFn: async () => {
            if (!exerciceId || !journal) return null;
            const r = await api.get("/api/piece/next_ref", {
                params: { exercice_id: exerciceId, journal, width: 5 },
            });
            setPieceRef(r.data.next_ref);
            return r.data;
        },
        enabled: false,
    });

    useEffect(() => {
        if (journal) refetchNext();
    }, [journal]);

    const addLine = useCallback(() => {
        const last = [...rows].reverse().find(r => !r.markedDeleted);
        const patch = {
            date: last?.date ?? new Date().toISOString().slice(0, 10),
            lib: last?.lib ?? "",
        };
        dispatch({ type: "add", row: patch });
    }, [rows, dispatch]);

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                e.preventDefault();
                addLine();
            }
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [addLine]);

    const totals = useTotals(rows);
    const canSubmit =
        !!journal && !!pieceRef && rows.length > 0 && totals.isBalanced && !totals.hasAmountErrors && !totals.bothSidesFilled;

    const mutate = useMutation({
        mutationFn: async () =>
            (
                await api.post("/api/piece/commit", {
                    exercice_id: exerciceId,
                    journal,
                    piece_ref: pieceRef,
                    changes: rows
                        .filter((r) => !r.markedDeleted)
                        .map((r) => ({
                            op: "add" as const,
                            date: r.date,
                            accnum: r.accnum,
                            acclib: r.acclib,
                            lib: r.lib,
                            debit_minor: toCents(r.debit),
                            credit_minor: toCents(r.credit),
                        })),
                })
            ).data,
        onSuccess: async () => {
            qc.invalidateQueries({ queryKey: ["entries"] });
            qc.invalidateQueries({ queryKey: ["balance"] });
            setBanner({ type: "success", message: "Pièce enregistrée." });
            dispatch({ type: "set", rows: [makeRow()] });
            await refetchNext();
        },
        onError: (err: any) => {
            const msg = err?.response?.data?.message || err?.message || "Erreur inconnue.";
            setBanner({ type: "error", message: msg });
        },
    });


    const updateRow = (uid: string, patch: Partial<typeof rows[number]>) => dispatch({ type: "update", uid, patch });
    const deleteRow = (uid: string, isNew: boolean) => dispatch({ type: "delete", uid, isNew });
    const undoDelete = (uid: string) => dispatch({ type: "undoDelete", uid });

    return (
        <div className="space-y-3">
            <h1 className="text-xl font-semibold">Nouvelle pièce</h1>

            {banner && (
                <div
                    className={`px-3 py-2 rounded ${banner.type === "success" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-700"
                        }`}
                >
                    {banner.message}
                </div>
            )}

            <div className="flex gap-3 items-end">
                <div>
                    <label htmlFor="journal" className="block text-sm">Journal</label>
                    <input id="journal" className="border px-2 py-1" value={journal} onChange={(e) => setJournal(e.target.value.trim())} placeholder="VT" />
                </div>
                <div>
                    <label htmlFor="pieceRef" className="block text-sm">Numéro de pièce</label>
                    <input id="pieceRef" className="border px-2 py-1" value={pieceRef} onChange={(e) => setPieceRef(e.target.value)} />
                </div>
                <div className="ml-auto text-sm">
                    <div>Total Débit: {totals.debit.toFixed(2)}</div>
                    <div>Total Crédit: {totals.credit.toFixed(2)}</div>
                    <div className={totals.isBalanced ? "text-green-600" : "text-red-600"}>Différence: {totals.diff.toFixed(2)}</div>
                </div>
            </div>

            <PieceRowsTable
                rows={rows}
                itemsByUid={itemsByUid}
                onAccSuggest={onAccSuggest}
                clearSuggest={clearSuggest}
                updateRow={updateRow}
                deleteRow={deleteRow}
                undoDelete={undoDelete}
            />

            {!totals.isBalanced && <div className="text-red-600 text-sm">La pièce doit être équilibrée pour valider.</div>}
            {totals.bothSidesFilled && (
                <div className="text-red-600 text-sm">Une ligne ne doit pas avoir simultanément Débit et Crédit.</div>
            )}

            <div className="flex gap-2">
                <button type="button" className="border px-3 py-1" onClick={addLine} title="Ctrl/Cmd + Entrée">
                    + Nouvelle ligne
                </button>
                <button type="button" className="border px-3 py-1 disabled:opacity-50" disabled={!canSubmit || mutate.isPending} onClick={() => mutate.mutate()}>
                    {mutate.isPending ? "Enregistrement…" : "Valider"}
                </button>
            </div>
        </div>
    );
}
