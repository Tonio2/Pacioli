import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useParams } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { useEffect, useRef, useState } from 'react'

type Row = {
  id?: number
  date: string
  jnl: string
  piece_ref: string
  accnum: string
  acclib: string
  lib: string
  debit: number
  credit: number
  _op?: 'keep' | 'add' | 'modify' | 'delete'
  _accountExists?: boolean
}

type SuggestItem = { account_id: number; accnum: string; acclib: string }

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
  const [suggest, setSuggest] = useState<Record<number, SuggestItem[]>>({})
  const debounceRef = useRef<Record<number, any>>({})

  useEffect(() => {
    if (data?.rows) {
      setRows(
        data.rows.map((r: any) => ({
          ...r,
          _op: 'keep',
          _accountExists: !!r.accnum, // s'il y a un compte lié, on considère existant
        })),
      )
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
          return {
            op: 'add',
            date: r.date,
            accnum: r.accnum,
            acclib: r.acclib, // utilisé seulement si on crée le compte
            lib: r.lib,
            debit: r.debit,
            credit: r.credit,
          }
        if (r._op === 'delete') return { op: 'delete', entry_id: r.id }
        if (r._op === 'modify')
          return {
            op: 'modify',
            entry_id: r.id,
            date: r.date,
            accnum: r.accnum, // si changé, on reliera au nouveau compte (créé si besoin)
            acclib: r.acclib, // ignoré si le compte existe déjà
            lib: r.lib,
            debit: r.debit,
            credit: r.credit,
          }
        return null
      })
      .filter(Boolean)

    mutate.mutate({ client_id: clientId, exercice_id: exerciceId, journal: jnl, piece_ref, changes })
  }

  const onAccnumChange = (idx: number, value: string) => {
    setRows((prev) =>
      prev.map((x, i) =>
        i === idx ? { ...x, accnum: value, _op: x._op === 'add' ? 'add' : 'modify' } : x,
      ),
    )

    // Debounce suggest + lookup
    if (debounceRef.current[idx]) clearTimeout(debounceRef.current[idx])
    debounceRef.current[idx] = setTimeout(async () => {
      // 1) Suggest pour dropdown
      if (value && value.length >= 2 && clientId) {
        const resp = await api.get('/api/accounts/suggest', { params: { client_id: clientId, q: value, limit: 10 } })
        setSuggest((s) => ({ ...s, [idx]: resp.data.items || [] }))
      } else {
        setSuggest((s) => ({ ...s, [idx]: [] }))
      }
      // 2) Lookup pour auto-remplir acclib
      if (clientId) {
        const res = await api.get('/api/accounts/lookup', { params: { client_id: clientId, accnum: value } })
        if (res.data.exists) {
          setRows((prev) =>
            prev.map((x, i) =>
              i === idx ? { ...x, acclib: res.data.acclib, _accountExists: true } : x,
            ),
          )
        } else {
          setRows((prev) =>
            prev.map((x, i) =>
              i === idx ? { ...x, _accountExists: false } : x,
            ),
          )
        }
      }
    }, 300)
  }

  const applySuggest = (idx: number, item: SuggestItem) => {
    setRows((prev) =>
      prev.map((x, i) =>
        i === idx
          ? {
              ...x,
              accnum: item.accnum,
              acclib: item.acclib,
              _accountExists: true,
              _op: x._op === 'add' ? 'add' : 'modify',
            }
          : x,
      ),
    )
    setSuggest((s) => ({ ...s, [idx]: [] }))
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
              acclib: '',
              lib: '',
              debit: 0,
              credit: 0,
              _accountExists: false,
            },
          ])
        }
      >
        + Ajouter ligne
      </button>

      <table className="min-w-full border border-gray-300 text-sm rounded-lg overflow-hidden shadow">
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
        <tbody>
          {rows.map((r, idx) => (
            <tr key={idx} className="odd:bg-white even:bg-gray-50 hover:bg-blue-50 transition">
              <td className="border border-gray-200 px-2 py-2">
                <input
                  type="date"
                  className="w-full border rounded px-2 py-1"
                  value={r.date}
                  onChange={(e) =>
                    setRows(rows.map((x, i) => (i === idx ? { ...x, date: e.target.value, _op: x._op === 'add' ? 'add' : 'modify' } : x)))
                  }
                />
              </td>

              {/* Compte + dropdown */}
              <td className="border border-gray-200 px-2 py-2 relative">
                <input
                  className="w-full border rounded px-2 py-1"
                  value={r.accnum}
                  onChange={(e) => onAccnumChange(idx, e.target.value)}
                  onBlur={() => setTimeout(() => setSuggest((s) => ({ ...s, [idx]: [] })), 150)}
                />
                {suggest[idx] && suggest[idx].length > 0 && (
                  <div className="absolute z-10 bg-white border rounded shadow top-full left-0 right-0 max-h-48 overflow-auto">
                    {suggest[idx].map((it) => (
                      <div
                        key={it.account_id}
                        className="px-2 py-1 hover:bg-gray-100 cursor-pointer"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => applySuggest(idx, it)}
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
                  placeholder={r._accountExists ? 'Compte existant' : 'Saisir libellé du compte'}
                  onChange={(e) =>
                    setRows(rows.map((x, i) => (i === idx ? { ...x, acclib: e.target.value, _op: x._op === 'add' ? 'add' : 'modify' } : x)))
                  }
                />
              </td>

              {/* Libellé écriture */}
              <td className="border border-gray-200 px-2 py-2">
                <input
                  className="w-full border rounded px-2 py-1 w-96"
                  value={r.lib}
                  onChange={(e) =>
                    setRows(rows.map((x, i) => (i === idx ? { ...x, lib: e.target.value, _op: x._op === 'add' ? 'add' : 'modify' } : x)))
                  }
                />
              </td>

              <td className="border border-gray-200 px-2 py-2 text-right">
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
              <td className="border border-gray-200 px-2 py-2 text-right">
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
              <td className="border border-gray-200 px-2 py-2 text-center">
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
