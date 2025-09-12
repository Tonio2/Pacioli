import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useApp } from '../context/AppContext'
import { useState } from 'react'

type Row = {
    id: number
    created_at: string
    description: string
    counts_human: string
}

export default function HistoryPage() {
    const { clientId, exerciceId } = useApp()
    const qc = useQueryClient()
    const [order] = useState<'asc' | 'desc'>('asc')

    const historyQ = useQuery({
        queryKey: ['history', clientId, exerciceId, order],
        queryFn: async () =>
            (await api.get('/api/history', { params: { client_id: clientId, exercice_id: exerciceId, order } })).data,
        enabled: !!clientId && !!exerciceId,
    })

    const update = useMutation({
        mutationFn: async (p: { id: number; description: string }) =>
            (await api.patch(`/api/history/${p.id}`, null, { params: { description: p.description } })).data,
        onSuccess: () => qc.invalidateQueries({ queryKey: ['history'] }),
    })

    const exportTxt = () => {
        if (!clientId || !exerciceId) return
        const url = `/api/history/export?client_id=${clientId}&exercice_id=${exerciceId}&order=${order}`
        // ouvre le téléchargement
        window.open(url, '_blank')
    }

    const rows: Row[] = historyQ.data?.rows ?? []

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-3">
                <h1 className="text-xl font-semibold">Historique</h1>
                <button className="border px-3 py-1 rounded" onClick={exportTxt}>Export TXT</button>
            </div>

            <table className="min-w-full border border-gray-300 text-sm rounded-lg overflow-hidden shadow">
                <thead className="bg-gray-100">
                    <tr>
                        <th className="border border-gray-300 px-3 py-2 text-left w-56">Date</th>
                        <th className="border border-gray-300 px-3 py-2 text-left">Counts</th>
                        <th className="border border-gray-300 px-3 py-2 text-left w-1/2">Description</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((r) => (
                        <tr key={r.id} className="odd:bg-white even:bg-gray-50">
                            <td className="border border-gray-200 px-3 py-2">{new Date(r.created_at).toLocaleString()}</td>
                            <td className="border border-gray-200 px-3 py-2 whitespace-pre">{r.counts_human}</td>
                            <td className="border border-gray-200 px-3 py-2">
                                <input
                                    className="w-full border rounded px-2 py-1"
                                    defaultValue={r.description}
                                    onBlur={(e) => update.mutate({ id: r.id, description: e.target.value })}
                                />
                            </td>
                        </tr>
                    ))}
                    {rows.length === 0 && (
                        <tr>
                            <td colSpan={3} className="text-center text-gray-500 px-3 py-6">Aucun événement pour cet exercice.</td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    )
}
