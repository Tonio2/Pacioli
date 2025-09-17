import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import DataTable from '../components/DataTable'
import { type ColumnDef } from '@tanstack/react-table'
import { useApp } from '../context/AppContext'
import { Link, useSearchParams } from 'react-router-dom'
import { useCallback } from 'react'
import { fmtCents } from '../modules/utils/amount'

type Row = { accnum: string; acclib: string; debit: number; credit: number; solde: number; count: number }

export default function Balance() {
    const { clientId, exerciceId } = useApp()
    const [sp] = useSearchParams()

    const { data, isFetching } = useQuery({
        queryKey: ['balance', clientId, exerciceId],
        queryFn: async () =>
            (await api.get('/api/balance', { params: { client_id: clientId, exercice_id: exerciceId } })).data,
        enabled: !!clientId && !!exerciceId,
    })

    const makeEntriesSearch = useCallback((accnum: string) => {
        const next = new URLSearchParams();
        const c = sp.get('client');
        const e = sp.get('exercice');
        if (c) next.set('client', c);
        if (e) next.set('exercice', e);
        next.set('compte', accnum);              // << ajoute le filtre compte
        next.set('sort', 'date,id');             // (optionnel) tri par défaut
        return `?${next.toString()}`;
    }, [sp]);

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
            cell: (info) => {
                const acc = info.getValue<string>();
                return (
                    <Link className="underline" to={{
                        pathname: "/entries",
                        search: makeEntriesSearch(acc),
                    }}>
                        {info.getValue<string>()}
                    </Link>
                )
            },
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
