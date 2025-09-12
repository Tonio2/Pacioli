// src/pages/Import.tsx
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useApp } from '../context/AppContext'
import { api } from '../api/client'
import { useState } from 'react'

type ImportResponse = {
  added: number
  warnings: { unbalanced_pieces: { jnl: string; piece_ref: string; total_debit: number; total_credit: number }[] }
}

export default function ImportPage() {
  const { clientId, exerciceId } = useApp()
  const qc = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [resp, setResp] = useState<ImportResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const res = await api.post('/api/imports/csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return res.data as ImportResponse
    },
    onSuccess: (data) => {
      setResp(data)
      setError(null)
      // invalider les caches utiles
      qc.invalidateQueries({ queryKey: ['balance', clientId, exerciceId] })
      qc.invalidateQueries({ queryKey: ['entries', clientId, exerciceId] })
      qc.invalidateQueries({ queryKey: ['checks', clientId, exerciceId] })
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.detail || e?.message || 'Erreur inconnue'
      setError(String(msg))
      setResp(null)
    },
  })

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return setError('Choisis un fichier CSV')
    if (!clientId || !exerciceId) return setError('Sélectionne un client et un exercice')

    const fd = new FormData()
    fd.append('client_id', String(clientId))
    fd.append('exercice_id', String(exerciceId))
    fd.append('file', file)

    mutation.mutate(fd)
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-xl font-semibold">Importer des écritures (CSV)</h1>

      <div className="text-sm text-gray-700">
        <p>Colonnes obligatoires (en-têtes exacts, ordre libre) :</p>
        <code className="block bg-gray-50 border p-2 mt-1 rounded">
          jnl, accnum, acclib, date, lib, pieceRef, debit, credit
        </code>
        <p className="mt-2">
          Formats acceptés : dates <code>DD/MM/YYYY</code> ou <code>YYYY-MM-DD</code> ; décimales <code>,</code> ou <code>.</code>.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-3">
        <input
          type="file"
          accept=".csv,.txt"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="block"
        />
        <button
          type="submit"
          disabled={mutation.isPending}
          className="border px-3 py-1 rounded disabled:opacity-50"
        >
          {mutation.isPending ? 'Import en cours…' : 'Importer'}
        </button>
      </form>

      {error && (
        <div className="border border-red-300 bg-red-50 text-red-800 p-3 rounded">
          <strong>Erreur :</strong> {error}
        </div>
      )}

      {resp && (
        <div className="space-y-3">
          <div className="border border-green-300 bg-green-50 text-green-800 p-3 rounded">
            <div><strong>{resp.added}</strong> écritures importées.</div>
          </div>
          {resp.warnings?.unbalanced_pieces?.length > 0 && (
            <div className="border border-amber-300 bg-amber-50 text-amber-900 p-3 rounded">
              <div className="font-semibold mb-2">Pièces déséquilibrées (sur tout l’exercice) :</div>
              <table className="min-w-full border text-sm">
                <thead>
                  <tr>
                    <th className="border p-1 text-left">Journal</th>
                    <th className="border p-1 text-left">Pièce</th>
                    <th className="border p-1 text-right">Total Débit</th>
                    <th className="border p-1 text-right">Total Crédit</th>
                  </tr>
                </thead>
                <tbody>
                  {resp.warnings.unbalanced_pieces.map((u, i) => (
                    <tr key={i} className="odd:bg-gray-50">
                      <td className="border p-1">{u.jnl}</td>
                      <td className="border p-1">{u.piece_ref}</td>
                      <td className="border p-1 text-right">{u.total_debit.toFixed(2)}</td>
                      <td className="border p-1 text-right">{u.total_credit.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <div className="text-sm text-gray-600">
        Astuce : garde un fichier modèle pour ne jamais te tromper sur les en-têtes 😉
      </div>
    </div>
  )
}
