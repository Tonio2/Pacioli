// src/pages/PiecePage.tsx
import { useEffect, useReducer, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useParams } from "react-router-dom";
import { useApp } from "../context/AppContext";

import { useTotals } from "../modules/pieces/useTotals";
import { rowsReducer, makeRow } from "../modules/pieces/rowsReducer";
import { useAccountSuggest } from "../modules/pieces/useAccountSuggest";
import { diffChanges } from "../modules/pieces/diff";
import type { Row } from "../modules/pieces/types";
import PieceRowsTable from "../components/PieceRowsTable";

export default function PiecePage() {
    const { jnl, piece_ref } = useParams();
    const { clientId, exerciceId } = useApp();
    const qc = useQueryClient();

    const { data } = useQuery({
        queryKey: ["piece", clientId, exerciceId, jnl, piece_ref],
        queryFn: async () =>
            (
                await api.get("/api/piece", {
                    params: { client_id: clientId, exercice_id: exerciceId, journal: jnl, piece_ref },
                })
            ).data,
        enabled: !!clientId && !!exerciceId && !!jnl && !!piece_ref,
    });

    const [rows, dispatch] = useReducer(rowsReducer, []);
    const originalRowsRef = useRef<Row[]>([]);
    const { itemsByUid, onChange: onAccSuggest, clear: clearSuggest } = useAccountSuggest(
        clientId as number | undefined
    );

    useEffect(() => {
        if (data?.rows) {
            const next: Row[] = data.rows.map((r: any) =>
                makeRow({
                    id: r.id,
                    date: r.date,
                    jnl: r.jnl,
                    piece_ref: r.piece_ref,
                    accnum: r.accnum ?? "",
                    acclib: r.acclib ?? "",
                    lib: r.lib ?? "",
                    debit: r.debit != null ? String(r.debit) : "",
                    credit: r.credit != null ? String(r.credit) : "",
                    _accountExists: !!r.accnum,
                })
            );
            originalRowsRef.current = next.map((r) => ({ ...r })); // snapshot
            dispatch({ type: "set", rows: next });
        } else {
            originalRowsRef.current = [];
            dispatch({ type: "set", rows: [] });
        }
    }, [data?.rows, clientId, exerciceId, jnl, piece_ref]);

    // Raccourci global Ctrl/Cmd + Entrée => ajouter ligne
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                e.preventDefault();
                addLine();
            }
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [jnl, piece_ref]);

    const totals = useTotals(rows);
    const canSubmit = rows.length > 0 && totals.isBalanced && !totals.hasAmountErrors && !totals.bothSidesFilled;

    const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);

    const mutate = useMutation({
        mutationFn: async (payload: any) => (await api.post("/api/piece/commit", payload)).data,
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["entries"] });
            qc.invalidateQueries({ queryKey: ["balance"] });
            qc.invalidateQueries({ queryKey: ["piece"] });
            setBanner({ type: "success", message: "Pièce enregistrée." });
        },
        onError: (err: any) => {
            const msg = err?.response?.data?.message || err?.message || "Erreur inconnue.";
            setBanner({ type: "error", message: msg });
        },
    });

    const submit = () => {
        const changes = diffChanges(originalRowsRef.current, rows);
        mutate.mutate({
            client_id: clientId,
            exercice_id: exerciceId,
            journal: jnl,
            piece_ref,
            changes,
        });
    };

    const addLine = () =>
        dispatch({
            type: "add",
            row: {
                date: new Date().toISOString().slice(0, 10),
                jnl: jnl!,
                piece_ref: piece_ref!,
            },
        });

    const updateRow = (uid: string, patch: Partial<Row>) => dispatch({ type: "update", uid, patch });
    const deleteRow = (uid: string, isNew: boolean) => dispatch({ type: "delete", uid, isNew });
    const undoDelete = (uid: string) => dispatch({ type: "undoDelete", uid });

    return (
        <div className="space-y-3">
            <h1 className="text-xl font-semibold">
                Pièce {jnl} / {piece_ref}
            </h1>

            {banner && (
                <div
                    className={`px-3 py-2 rounded ${banner.type === "success" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-700"
                        }`}
                >
                    {banner.message}
                </div>
            )}

            <div className="flex items-center justify-between">
                <button type="button" className="border px-3 py-1" onClick={addLine} title="Ctrl/Cmd + Entrée">
                    + Ajouter ligne
                </button>
                <div className="text-sm">
                    <div>Total Débit: {totals.debit.toFixed(2)}</div>
                    <div>Total Crédit: {totals.credit.toFixed(2)}</div>
                    <div className={totals.isBalanced ? "text-green-600" : "text-red-600"}>
                        Différence: {totals.diff.toFixed(2)}
                    </div>
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

            <div className="flex items-center justify-between">
                <div className="text-sm">
                    {totals.hasAmountErrors && (
                        <span className="text-red-600">Corrige les montants invalides avant d’enregistrer.</span>
                    )}
                    {totals.bothSidesFilled && (
                        <span className="ml-3 text-red-600">Une ligne ne doit pas avoir à la fois Débit et Crédit.</span>
                    )}
                    {!totals.isBalanced && <span className="ml-3 text-red-600">La pièce doit être équilibrée.</span>}
                </div>
                <button
                    type="button"
                    className="border px-3 py-1 disabled:opacity-50"
                    onClick={submit}
                    disabled={mutate.isPending || !canSubmit}
                >
                    {mutate.isPending ? "Enregistrement…" : "Enregistrer"}
                </button>
            </div>
        </div>
    );
}
