import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useParams } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { useEffect, useState } from 'react'

type Row = {
    id?: number
    date: string
    jnl: string
    piece_ref: string
    accnum: string
    lib: string
    debit: number
    credit: number
    _op?: 'keep' | 'add' | 'modify' | 'delete'
}

export default function PiecePage() {
    const { jnl, piece_ref } = useParams()
    const { clientId, exerciceId } = useApp()
    const qc = useQueryClient()

    const { data } = useQuery({
        queryKey: ['piece', clientId, exerciceId, jnl, piece_ref],
        queryFn: async () =>
            (await api.get('/api/piece', {
                params: { client_id: clientId, exercice_id: exerciceId, journal: jnl, piece_ref },
            })).data,
        enabled: !!clientId && !!exerciceId && !!jnl && !!piece_ref,
    })

    const [rows, setRows] = useState<Row[]>([])

    useEffect(() => {
        if (data?.rows) {
            setRows(data.rows.map((r: any) => ({ ...r, _op: 'keep' })))
        } else {
            setRows([])
        }
    }, [data?.rows, clientId, exerciceId, jnl, piece_ref])

    const mutate = useMutation({
        mutationFn: async (payload: any) => (await api.post('/api/piece/commit', payload)).data,
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['entries'] })
            qc.invalidateQueries({ queryKey: ['balance'] })
            qc.invalidateQueries({ queryKey: ['piece'] })
            alert('Enregistré')
        },
    })

    const submit = () => {
        const changes = rows
            .map((r) => {
                if (r._op === 'add')
                    return { op: 'add', date: r.date, accnum: r.accnum, lib: r.lib, debit: r.debit, credit: r.credit }
                if (r._op === 'delete') return { op: 'delete', entry_id: r.id }
                if (r._op === 'modify')
                    return { op: 'modify', entry_id: r.id, date: r.date, accnum: r.accnum, lib: r.lib, debit: r.debit, credit: r.credit }
                return null
            })
            .filter(Boolean)

        mutate.mutate({ client_id: clientId, exercice_id: exerciceId, journal: jnl, piece_ref, changes })
    }

    return (
        <div className="space-y-3">
            <h1 className="text-xl font-semibold">
                Pièce {jnl} / {piece_ref}
            </h1>

            <button
                className="border px-3 py-1"
                onClick={() =>
                    setRows([
                        ...rows,
                        {
                            _op: 'add',
                            date: new Date().toISOString().slice(0, 10),
                            jnl: jnl!,
                            piece_ref: piece_ref!,
                            accnum: '',
                            lib: '',
                            debit: 0,
                            credit: 0,
                        },
                    ])
                }
            >
                + Ajouter ligne
            </button>

            <table className="min-w-full border border-gray-300 text-sm rounded-lg overflow-hidden shadow">
                <thead className='bg-gray-100'>
                    <tr>
                        <th className='border border-gray-300 px-3 py-2 text-left w-36'>Date</th>
                        <th className='border border-gray-300 px-3 py-2 text-left w-36'>Compte</th>
                        <th className='border border-gray-300 px-3 py-2 text-left'>Libellé</th>
                        <th className='border border-gray-300 px-3 py-2 text-right w-32'>Débit</th>
                        <th className='border border-gray-300 px-3 py-2 text-right w-32'>Crédit</th>
                        <th className='border border-gray-300 px-3 py-2 text-center w-28'>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((r, idx) => (
                        <tr key={idx} className="odd:bg-white even:bg-gray-50 hover:bg-blue-50 transition">
                            <td className='border border-gray-200 px-2 py-2'>
                                <input
                                    type='date'
                                    className="w-full border rounded px-2 py-1"
                                    value={r.date}
                                    onChange={(e) =>
                                        setRows(rows.map((x, i) => (i === idx ? { ...x, date: e.target.value, _op: x._op === 'add' ? 'add' : 'modify' } : x)))
                                    }
                                />
                            </td>
                            <td className='border border-gray-200 px-2 py-2'>
                                <input
                                    className="w-full border rounded px-2 py-1"
                                    value={r.accnum}
                                    onChange={(e) =>
                                        setRows(rows.map((x, i) => (i === idx ? { ...x, accnum: e.target.value, _op: x._op === 'add' ? 'add' : 'modify' } : x)))
                                    }
                                />
                            </td>
                            <td className='border border-gray-200 px-2 py-2'>
                                <input
                                    className="w-full border rounded px-2 py-1 w-96"
                                    value={r.lib}
                                    onChange={(e) =>
                                        setRows(rows.map((x, i) => (i === idx ? { ...x, lib: e.target.value, _op: x._op === 'add' ? 'add' : 'modify' } : x)))
                                    }
                                />
                            </td>
                            <td className='border border-gray-200 px-2 py-2 text-right'>
                                <input
                                    className="w-full border rounded px-2 py-1 text-right"
                                    value={r.debit}
                                    onChange={(e) =>
                                        setRows(
                                            rows.map((x, i) =>
                                                i === idx ? { ...x, debit: parseFloat(e.target.value || '0'), _op: x._op === 'add' ? 'add' : 'modify' } : x,
                                            ),
                                        )
                                    }
                                />
                            </td>
                            <td className='border border-gray-200 px-2 py-2 text-right'>
                                <input
                                    className="w-full border rounded px-2 py-1 text-right"
                                    value={r.credit}
                                    onChange={(e) =>
                                        setRows(
                                            rows.map((x, i) =>
                                                i === idx ? { ...x, credit: parseFloat(e.target.value || '0'), _op: x._op === 'add' ? 'add' : 'modify' } : x,
                                            ),
                                        )
                                    }
                                />
                            </td>
                            <td className='border border-gray-200 px-2 py-2 text-center'>
                                <button className="border px-2 py-1" onClick={() => setRows(rows.map((x, i) => (i === idx ? { ...x, _op: 'delete' } : x)))}>
                                    Supprimer
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <button className="border px-3 py-1" onClick={submit} disabled={mutate.isPending}>
                {mutate.isPending ? 'Enregistrement…' : 'Enregistrer'}
            </button>
        </div>
    )
}
