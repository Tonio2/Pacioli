// src/components/PieceRowsTable.tsx
import { useEffect, useMemo, useState } from "react";
import { isValidAmount } from "../modules/utils/amount";
import type { Row, SuggestItem } from "../modules/pieces/types";

type Props = {
    rows: Row[];
    itemsByUid: Record<string, SuggestItem[]>;
    onAccSuggest: (uid: string, value: string, onLookup: (res: { exists: boolean; acclib?: string }) => void) => void;
    clearSuggest: (uid: string) => void;
    updateRow: (uid: string, patch: Partial<Row>) => void;
    deleteRow: (uid: string, isNew: boolean) => void;
    undoDelete: (uid: string) => void;
};

export default function PieceRowsTable({
    rows,
    itemsByUid,
    onAccSuggest,
    clearSuggest,
    updateRow,
    deleteRow,
    undoDelete,
}: Props) {
    // index surligné dans les suggestions par ligne (uid)
    const [hiByUid, setHi] = useState<Record<string, number>>({});

    // Réinitialise l’index surligné lorsqu’une liste change / se vide
    useEffect(() => {
        const next: Record<string, number> = {};
        for (const r of rows) next[r.uid] = (itemsByUid[r.uid]?.length ?? 0) > 0 ? 0 : -1;
        setHi(next);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [JSON.stringify(Object.keys(itemsByUid)), JSON.stringify(Object.values(itemsByUid).map((l) => l?.length || 0))]);

    const headers = useMemo(
        () => (
            <thead className="bg-gray-100">
                <tr>
                    <th className="border border-gray-300 px-3 py-2 text-left w-36">Date</th>
                    <th className="border border-gray-300 px-3 py-2 text-left w-40">Compte</th>
                    <th className="border border-gray-300 px-3 py-2 text-left w-64">Libellé du compte</th>
                    <th className="border border-gray-300 px-3 py-2 text-left">Libellé écriture</th>
                    <th className="border border-gray-300 px-3 py-2 text-right w-32">Débit</th>
                    <th className="border border-gray-300 px-3 py-2 text-right w-32">Crédit</th>
                    <th className="border border-gray-300 px-3 py-2 text-center w-28">Actions</th>
                </tr>
            </thead>
        ),
        []
    );

    const onKeyDownAccnum = (e: React.KeyboardEvent<HTMLInputElement>, uid: string) => {
        const list = itemsByUid[uid] || [];
        const hasList = list.length > 0;
        const hi = hiByUid[uid] ?? -1;

        if (e.key === "Escape") {
            if (hasList) {
                e.preventDefault();
                clearSuggest(uid);
                setHi((s) => ({ ...s, [uid]: -1 }));
            }
        }

        if (e.key === "ArrowDown" && hasList) {
            e.preventDefault();
            const next = hi < 0 ? 0 : Math.min(hi + 1, list.length - 1);
            setHi((s) => ({ ...s, [uid]: next }));
        }

        if (e.key === "ArrowUp" && hasList) {
            e.preventDefault();
            const next = hi <= 0 ? 0 : hi - 1;
            setHi((s) => ({ ...s, [uid]: next }));
        }

        if (e.key === "Enter" && hasList) {
            e.preventDefault();
            const item = list[Math.max(0, hi)];
            if (item) {
                updateRow(uid, { accnum: item.accnum, acclib: item.acclib, _accountExists: true });
                clearSuggest(uid);
                setHi((s) => ({ ...s, [uid]: -1 }));
            }
        }
    };

    return (
        <table className="min-w-full border border-gray-300 text-sm rounded-lg shadow">
            {headers}
            <tbody>
                {rows.map((r) => {
                    const suggest = itemsByUid[r.uid] || [];
                    const hiIdx = hiByUid[r.uid] ?? -1;
                    return (
                        <tr
                            key={r.uid}
                            className={`odd:bg-white even:bg-gray-50 hover:bg-blue-50 transition ${r.markedDeleted ? "opacity-50 line-through" : ""
                                }`}
                        >
                            <td className="border border-gray-200 px-2 py-2">
                                <input
                                    type="date"
                                    className="w-full border rounded px-2 py-1"
                                    value={r.date}
                                    onChange={(e) => updateRow(r.uid, { date: e.target.value })}
                                />
                            </td>

                            {/* Compte + dropdown + clavier */}
                            <td className="border border-gray-200 px-2 py-2 relative">
                                <input
                                    className="w-full border rounded px-2 py-1"
                                    value={r.accnum}
                                    onKeyDown={(e) => onKeyDownAccnum(e, r.uid)}
                                    onChange={(e) => {
                                        const value = e.target.value;
                                        updateRow(r.uid, { accnum: value });
                                        onAccSuggest(r.uid, value, ({ exists, acclib }) =>
                                            updateRow(r.uid, { _accountExists: exists, ...(exists ? { acclib: acclib ?? "" } : {}) })
                                        );
                                    }}
                                    onBlur={() => setTimeout(() => clearSuggest(r.uid), 150)}
                                    aria-expanded={suggest.length > 0}
                                    aria-controls={`acc-suggest-${r.uid}`}
                                />
                                {suggest.length > 0 && (
                                    <div
                                        id={`acc-suggest-${r.uid}`}
                                        className="absolute z-10 bg-white border rounded shadow top-full left-0 right-0 max-h-48 overflow-auto"
                                        role="listbox"
                                    >
                                        {suggest.map((it, i) => (
                                            <div
                                                key={it.account_id}
                                                className={`px-2 py-1 cursor-pointer ${i === hiIdx ? "bg-blue-100" : "hover:bg-gray-100"
                                                    }`}
                                                onMouseDown={(e) => e.preventDefault()}
                                                onClick={() => {
                                                    updateRow(r.uid, { accnum: it.accnum, acclib: it.acclib, _accountExists: true });
                                                    clearSuggest(r.uid);
                                                    setHi((s) => ({ ...s, [r.uid]: -1 }));
                                                }}
                                                role="option"
                                                aria-selected={i === hiIdx}
                                            >
                                                <div className="font-mono">{it.accnum}</div>
                                                <div className="text-xs text-gray-600">{it.acclib}</div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </td>

                            {/* Libellé du compte */}
                            <td className="border border-gray-200 px-2 py-2">
                                <input
                                    className="w-full border rounded px-2 py-1"
                                    value={r.acclib}
                                    disabled={!!r._accountExists}
                                    placeholder={r._accountExists ? "Compte existant" : "Saisir libellé du compte"}
                                    onChange={(e) => updateRow(r.uid, { acclib: e.target.value })}
                                />
                            </td>

                            {/* Libellé écriture */}
                            <td className="border border-gray-200 px-2 py-2">
                                <input
                                    className="w-full border rounded px-2 py-1 w-96"
                                    value={r.lib}
                                    onChange={(e) => updateRow(r.uid, { lib: e.target.value })}
                                />
                            </td>

                            {/* Débit / Crédit */}
                            <td className="border border-gray-200 px-2 py-2 text-right">
                                <input
                                    inputMode="decimal"
                                    className={`w-full border rounded px-2 py-1 text-right ${r.debit !== "" && !isValidAmount(r.debit) ? "border-red-500 focus:ring-red-500" : ""
                                        }`}
                                    value={r.debit}
                                    onChange={(e) => updateRow(r.uid, { debit: e.target.value })}
                                    aria-invalid={r.debit !== "" && !isValidAmount(r.debit)}
                                />
                            </td>
                            <td className="border border-gray-200 px-2 py-2 text-right">
                                <input
                                    inputMode="decimal"
                                    className={`w-full border rounded px-2 py-1 text-right ${r.credit !== "" && !isValidAmount(r.credit) ? "border-red-500 focus:ring-red-500" : ""
                                        }`}
                                    value={r.credit}
                                    onChange={(e) => updateRow(r.uid, { credit: e.target.value })}
                                    aria-invalid={r.credit !== "" && !isValidAmount(r.credit)}
                                />
                            </td>

                            <td className="border border-gray-200 px-2 py-2 text-center">
                                {r.markedDeleted ? (
                                    <button type="button" className="border px-2 py-1" onClick={() => undoDelete(r.uid)}>
                                        Annuler
                                    </button>
                                ) : (
                                    <button
                                        type="button"
                                        className="border px-2 py-1"
                                        onClick={() => deleteRow(r.uid, !r.id)}
                                    >
                                        Supprimer
                                    </button>
                                )}
                            </td>
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}
