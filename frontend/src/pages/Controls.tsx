// frontend/src/pages/ControlsPage.tsx
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useApp } from '../context/AppContext'
import { Link } from 'react-router-dom'
import { useState } from 'react'

type PieceItem = { jnl: string; piece_ref: string; count: number; debit: number; credit: number; diff: number }
type PiecesResp = { items: PieceItem[]; total: number }
type JournalItem = { jnl: string; count: number; debit: number; credit: number; diff: number }
type JournalsResp = { items: JournalItem[]; total: number }

export default function ControlsPage() {
    const { clientId, exerciceId } = useApp()
    const [page, setPage] = useState(1)
    const pageSize = 100

    const pieces = useQuery({
        queryKey: ['controls-pieces', clientId, exerciceId, page, pageSize],
        queryFn: async () =>
            (await api.get('/api/controls/unbalanced-pieces', {
                params: { client_id: clientId, exercice_id: exerciceId, page, page_size: pageSize },
            })).data as PiecesResp,
        enabled: !!clientId && !!exerciceId,
    })

    const journals = useQuery({
        queryKey: ['controls-journals', clientId, exerciceId],
        queryFn: async () =>
            (await api.get('/api/controls/unbalanced-journals', {
                params: { client_id: clientId, exercice_id: exerciceId },
            })).data as JournalsResp,
        enabled: !!clientId && !!exerciceId,
    })

    const exportPiecesUrl = `/api/controls/unbalanced-pieces/export?client_id=${clientId}&exercice_id=${exerciceId}`
    const exportJournalsUrl = `/api/controls/unbalanced-journals/export?client_id=${clientId}&exercice_id=${exerciceId}`

    return (
        <div className="space-y-6">
            <h1 className="text-xl font-semibold">Contrôles</h1>

            {/* Pièces déséquilibrées */}
            <section className="space-y-3">
                <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Pièces déséquilibrées</h2>
                    <a className="border px-3 py-1 rounded hover:bg-gray-50" href={exportPiecesUrl}>
                        Export CSV
                    </a>
                </div>

                <table className="min-w-full border border-gray-300 text-sm rounded-lg overflow-hidden shadow">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="border px-3 py-2 text-left">Pièce</th>
                            <th className="border px-3 py-2 text-right w-32">Nb écritures</th>
                            <th className="border px-3 py-2 text-right w-32">Différence</th>
                        </tr>
                    </thead>
                    <tbody>
                        {pieces.data?.items?.length ? (
                            pieces.data.items.map((it) => (
                                <tr key={`${it.jnl}:${it.piece_ref}`} className="odd:bg-white even:bg-gray-50 hover:bg-blue-50 transition">
                                    <td className="border px-3 py-2">
                                        <Link className="text-blue-600 hover:underline" to={`/piece/${encodeURIComponent(it.jnl)}/${encodeURIComponent(it.piece_ref)}`}>
                                            {it.jnl} / {it.piece_ref}
                                        </Link>
                                    </td>
                                    <td className="border px-3 py-2 text-right">{it.count}</td>
                                    <td className={`border px-3 py-2 text-right ${it.diff !== 0 ? 'text-red-600 font-medium' : ''}`}>{it.diff.toFixed(2)}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td className="border px-3 py-2 text-center text-gray-500" colSpan={3}>
                                    {pieces.isFetching ? 'Chargement…' : 'Aucune pièce déséquilibrée 🎉'}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>

                {/* Pagination simple */}
                <div className="flex items-center gap-2">
                    <button
                        className="border px-3 py-1 rounded disabled:opacity-50"
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page <= 1}
                    >
                        ← Précédent
                    </button>
                    <span>Page {page}</span>
                    <button
                        className="border px-3 py-1 rounded disabled:opacity-50"
                        onClick={() => {
                            const total = pieces.data?.total || 0
                            const maxPage = Math.max(1, Math.ceil(total / pageSize))
                            setPage((p) => Math.min(maxPage, p + 1))
                        }}
                        disabled={(pieces.data?.total || 0) <= page * pageSize}
                    >
                        Suivant →
                    </button>
                </div>
            </section>

            {/* Journaux déséquilibrés */}
            <section className="space-y-3">
                <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Journaux déséquilibrés</h2>
                    <a className="border px-3 py-1 rounded hover:bg-gray-50" href={exportJournalsUrl}>
                        Export CSV
                    </a>
                </div>

                <table className="min-w-full border border-gray-300 text-sm rounded-lg overflow-hidden shadow">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="border px-3 py-2 text-left">Journal</th>
                            <th className="border px-3 py-2 text-right w-32">Nb écritures</th>
                            <th className="border px-3 py-2 text-right w-32">Différence</th>
                        </tr>
                    </thead>
                    <tbody>
                        {journals.data?.items?.length ? (
                            journals.data.items.map((it) => (
                                <tr key={it.jnl} className="odd:bg-white even:bg-gray-50 hover:bg-blue-50 transition">
                                    <td className="border px-3 py-2">
                                        <Link className="text-blue-600 hover:underline" to={`/entries?jnl=${encodeURIComponent(it.jnl)}`}>
                                            {it.jnl}
                                        </Link>
                                    </td>
                                    <td className="border px-3 py-2 text-right">{it.count}</td>
                                    <td className={`border px-3 py-2 text-right ${it.diff !== 0 ? 'text-red-600 font-medium' : ''}`}>{it.diff.toFixed(2)}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td className="border px-3 py-2 text-center text-gray-500" colSpan={3}>
                                    {journals.isFetching ? 'Chargement…' : 'Aucun journal déséquilibré 🎉'}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </section>
        </div>
    )
}
