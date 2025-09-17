import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useApp } from '../context/AppContext'
import { Link } from 'react-router-dom'
import { fmtCents } from '../modules/utils/amount'

// Types côté front
interface CentralisateurRow {
    jnl: string
    jnl_lib: string
    count: number
    debit_minor: number
    credit_minor: number
    diff_minor: number
}

interface CentralisateurResp {
    exercice: { date_start: string; date_end: string }
    journals: { jnl: string; jnl_lib: string }[]
    months: { month: string; rows: CentralisateurRow[] }[]
}

export default function ControlsPage() {
    const { clientId, exerciceId } = useApp()
    const qc = useQueryClient()
    const [busyKey, setBusyKey] = useState<string | null>(null) // anti double-clic: `${month}|${jnl}`

    const { data, isFetching } = useQuery<CentralisateurResp>({
        queryKey: ['centralisateur', clientId, exerciceId],
        queryFn: async () => (await api.get('/api/centralisateur', { params: { client_id: clientId, exercice_id: exerciceId } })).data,
        enabled: !!clientId && !!exerciceId,
        staleTime: 30_000,
    })

    const months = data?.months ?? []

    const handleDelete = async (month: string, jnl: string) => {
        if (!exerciceId) return
        if (!confirm(`Supprimer TOUTES les écritures du journal ${jnl} pour ${month} ?`)) return
        const key = `${month}|${jnl}`
        try {
            setBusyKey(key)
            const res = await api.delete('/api/centralisateur/entries', { params: { exercice_id: exerciceId, jnl, month } })
            alert(`${res.data?.deleted_count ?? 0} écriture(s) supprimée(s).`)
            qc.invalidateQueries({ queryKey: ['centralisateur', clientId, exerciceId] })
        } catch (e: any) {
            alert(e?.response?.data?.detail || 'Erreur lors de la suppression')
        } finally {
            setBusyKey(null)
        }
    }

    const monthLabel = (m: string) => {
        // m = "YYYY-MM" → on peut afficher directement, simple et robuste
        return m
    }

    const lastDayOfMonth = (ym: string) => {
        const [y, m] = ym.split('-').map(Number)
        const d = new Date(y, m, 0) // JS: day 0 of next month gives last day of current
        const dd = String(d.getDate()).padStart(2, '0')
        return `${y}-${String(m).padStart(2, '0')}-${dd}`
    }

    const firstDayOfMonth = (ym: string) => `${ym}-01`

    const COLS = useMemo(() => ([
        <col key="jnl" style={{ width: '6rem' }} />,     // JNL
        <col key="lib" />,                                // Libellé
        <col key="count" style={{ width: '8rem' }} />,   // Nb écritures
        <col key="debit" style={{ width: '9rem' }} />,   // Débit
        <col key="credit" style={{ width: '9rem' }} />,  // Crédit
        <col key="solde" style={{ width: '9rem' }} />,   // Solde
        <col key="actions" style={{ width: '11rem' }} />,// Actions
    ]), [])

    return (
        <div className="space-y-6">
            <h1 className="text-xl font-semibold">Journal centralisateur</h1>

            {isFetching && months.length === 0 ? (
                <div className="text-sm text-gray-500">Chargement…</div>
            ) : null}

            {months.map(({ month, rows }) => (
                <section key={month} className="space-y-2">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold">{monthLabel(month)}</h2>
                    </div>

                    <table className="min-w-full border border-gray-300 text-sm rounded-lg overflow-hidden shadow [font-variant-numeric:tabular-nums]">
                        <colgroup>{COLS}</colgroup>
                        <thead className="bg-gray-100">
                            <tr>
                                <th className="border px-3 py-2 text-left">JNL</th>
                                <th className="border px-3 py-2 text-left">Libellé</th>
                                <th className="border px-3 py-2 text-right">Nb écritures</th>
                                <th className="border px-3 py-2 text-right">Débit</th>
                                <th className="border px-3 py-2 text-right">Crédit</th>
                                <th className="border px-3 py-2 text-right">Solde</th>
                                <th className="border px-3 py-2">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((r) => (
                                <tr key={`${month}:${r.jnl}`} className="odd:bg-white even:bg-gray-50">
                                    <td className="border px-3 py-2">
                                        <Link className="text-blue-600 hover:underline" to={`/entries?journal=${encodeURIComponent(r.jnl)}&min_date=${encodeURIComponent(firstDayOfMonth(month))}&max_date=${encodeURIComponent(lastDayOfMonth(month))}`}>
                                            {r.jnl}
                                        </Link>
                                    </td>
                                    <td className="border px-3 py-2">{r.jnl_lib}</td>
                                    <td className="border px-3 py-2 text-right">{r.count}</td>
                                    <td className="border px-3 py-2 text-right">{fmtCents(r.debit_minor)}</td>
                                    <td className="border px-3 py-2 text-right">{fmtCents(r.credit_minor)}</td>
                                    <td className={`border px-3 py-2 text-right ${r.diff_minor !== 0 ? 'text-red-600 font-medium' : ''}`}>{fmtCents(r.diff_minor)}</td>
                                    <td className="border px-3 py-2">
                                        <button
                                            className="border px-3 py-1 rounded disabled:opacity-50"
                                            onClick={() => handleDelete(month, r.jnl)}
                                            disabled={busyKey === `${month}|${r.jnl}`}
                                        >
                                            Supprimer écritures
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </section>
            ))}
        </div>
    )
}
