import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import DataTable from '../components/DataTable'
import { type ColumnDef } from '@tanstack/react-table'
import { useApp } from '../context/AppContext'
import { Link } from 'react-router-dom'
import { useCallback } from 'react'
import { fmtCents } from '../modules/utils/amount'

type Row = { accnum: string; acclib: string; debit: number; credit: number; solde: number; count: number }

export default function Balance() {
    const { clientId, exerciceId } = useApp()

    const { data, isFetching } = useQuery({
        queryKey: ['balance', clientId, exerciceId],
        queryFn: async () =>
            (await api.get('/api/balance', { params: { client_id: clientId, exercice_id: exerciceId } })).data,
        enabled: !!clientId && !!exerciceId,
    })

    const handleExport = useCallback(async () => {
        if (!clientId || !exerciceId) return
        const res = await api.get('/api/balance/export', {
            params: { client_id: clientId, exercice_id: exerciceId },
        })
        alert(`Fichier enregistré: ${res.data.saved_to}`)
    }, [clientId, exerciceId])

    const rows: Row[] = data?.rows ?? []
    const columns: ColumnDef<Row>[] = [
        {
            header: 'Compte',
            accessorKey: 'accnum',
            cell: (info) => (
                <Link className="underline" to={`/entries?compte=${info.getValue<string>()}`}>
                    {info.getValue<string>()}
                </Link>
            ),
        },
        { header: 'Libellé', accessorKey: 'acclib' },
        { header: 'Débit', accessorKey: 'debit_minor', cell: (info) => fmtCents(info.getValue<number>()) },
        { header: 'Crédit', accessorKey: 'credit_minor', cell: (info) => fmtCents(info.getValue<number>()) },
        { header: 'Solde', accessorKey: 'solde_minor', cell: (info) => fmtCents(info.getValue<number>()) },
        { header: 'N', accessorKey: 'count' },
    ]

    return (
        <div>
            <div className="mb-3 flex items-center justify-between">
                <h1 className="text-xl font-semibold">Balance</h1>
                <button
                    onClick={handleExport}
                    disabled={!clientId || !exerciceId || isFetching}
                    className="rounded-md px-3 py-1.5 text-sm font-medium border shadow-sm hover:bg-gray-50 disabled:opacity-50"
                    title="Exporter la balance (TSV)"
                >
                    Exporter
                </button>
            </div>
            <DataTable data={rows} columns={columns} />
        </div>
    )
}
