import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import DataTable from '../components/DataTable'
import { type ColumnDef } from '@tanstack/react-table'
import { useApp } from '../context/AppContext'
import { useSearchParams, Link } from 'react-router-dom'

type Row = { id:number; date:string; jnl:string; piece_ref:string; accnum:string; lib:string; debit:number; credit:number }

export default function Entries(){
  const { clientId, exerciceId } = useApp()
  const [sp] = useSearchParams()
  const params = Object.fromEntries(sp.entries())
  const { data } = useQuery({
    queryKey: ['entries', clientId, exerciceId, params],
    queryFn: async () => (await api.get('/api/entries', { params: { client_id: clientId, exercice_id: exerciceId, ...params } })).data,
    enabled: !!clientId && !!exerciceId
  })
  const rows: Row[] = data?.rows ?? []
  const columns: ColumnDef<Row>[] = [
    { header: 'Date', accessorKey: 'date' },
    { header: 'Jnl', accessorKey: 'jnl' },
    { header: 'Pièce', accessorKey: 'piece_ref', cell: i => <Link className="underline" to={`/piece/${i.row.original.jnl}/${i.row.original.piece_ref}`}>{i.getValue<string>()}</Link> },
    { header: 'Compte', accessorKey: 'accnum' },
    { header: 'Libellé', accessorKey: 'lib' },
    { header: 'Débit', accessorKey: 'debit' },
    { header: 'Crédit', accessorKey: 'credit' },
  ]
  return <div>
    <h1 className="text-xl font-semibold mb-3">Écritures</h1>
    <DataTable data={rows} columns={columns} />
  </div>
}
