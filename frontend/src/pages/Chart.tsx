import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useApp } from '../context/AppContext'

type Account = { id: number; accnum: string; acclib: string }
type Journal = { id: number; jnl: string; jnl_lib: string }

export default function ChartPage() {
    const { clientId } = useApp()
    const qc = useQueryClient()

    const accountsQ = useQuery({
        queryKey: ['accounts', clientId],
        queryFn: async () => (await api.get('/api/chart/accounts', { params: { client_id: clientId } })).data,
        enabled: !!clientId,
    })

    const journalsQ = useQuery({
        queryKey: ['journals', clientId],
        queryFn: async () => (await api.get('/api/chart/journals', { params: { client_id: clientId } })).data,
        enabled: !!clientId,
    })

    const updateAccount = useMutation({
        mutationFn: async (p: { id: number; acclib: string }) =>
            (await api.patch(`/api/chart/accounts/${p.id}`, null, { params: { acclib: p.acclib } })).data,
        onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts'] }),
    })

    const updateJournal = useMutation({
        mutationFn: async (p: { id: number; jnl_lib: string }) =>
            (await api.patch(`/api/chart/journals/${p.id}`, null, { params: { jnl_lib: p.jnl_lib } })).data,
        onSuccess: () => qc.invalidateQueries({ queryKey: ['journals'] }),
    })

    const exportAccounts = () => {
        if (!clientId) return
        window.open(`/api/chart/export/accounts?client_id=${clientId}`, '_blank')
    }

    const exportJournals = () => {
        if (!clientId) return
        window.open(`/api/chart/export/journals?client_id=${clientId}`, '_blank')
    }

    const accounts: Account[] = accountsQ.data ?? []
    const journals: Journal[] = journalsQ.data ?? []

    return (
        <div className="space-y-8">
            <div>
                <div className="flex items-center gap-3">
                    <h1 className="text-xl font-semibold">Plan comptable – Comptes</h1>
                    <button className="border px-3 py-1 rounded" onClick={exportAccounts}>Export JSON</button>
                </div>

                <table className="min-w-full border border-gray-300 text-sm mt-3 rounded-lg overflow-hidden shadow">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="border px-3 py-2 text-left w-32">Numéro</th>
                            <th className="border px-3 py-2 text-left">Libellé</th>
                        </tr>
                    </thead>
                    <tbody>
                        {accounts.map((a) => (
                            <tr key={a.id} className="odd:bg-white even:bg-gray-50">
                                <td className="border px-3 py-2">{a.accnum}</td>
                                <td className="border px-3 py-2">
                                    <input
                                        className="w-full border rounded px-2 py-1"
                                        defaultValue={a.acclib}
                                        onBlur={(e) => updateAccount.mutate({ id: a.id, acclib: e.target.value })}
                                    />
                                </td>
                            </tr>
                        ))}
                        {accounts.length === 0 && (
                            <tr>
                                <td colSpan={2} className="text-center text-gray-500 px-3 py-6">Aucun compte</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            <div>
                <div className="flex items-center gap-3">
                    <h1 className="text-xl font-semibold">Plan comptable – Journaux</h1>
                    <button className="border px-3 py-1 rounded" onClick={exportJournals}>Export JSON</button>
                </div>

                <table className="min-w-full border border-gray-300 text-sm mt-3 rounded-lg overflow-hidden shadow">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="border px-3 py-2 text-left w-32">Code</th>
                            <th className="border px-3 py-2 text-left">Libellé</th>
                        </tr>
                    </thead>
                    <tbody>
                        {journals.map((j) => (
                            <tr key={j.id} className="odd:bg-white even:bg-gray-50">
                                <td className="border px-3 py-2">{j.jnl}</td>
                                <td className="border px-3 py-2">
                                    <input
                                        className="w-full border rounded px-2 py-1"
                                        defaultValue={j.jnl_lib}
                                        onBlur={(e) => updateJournal.mutate({ id: j.id, jnl_lib: e.target.value })}
                                    />
                                </td>
                            </tr>
                        ))}
                        {journals.length === 0 && (
                            <tr>
                                <td colSpan={2} className="text-center text-gray-500 px-3 py-6">Aucun journal</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
