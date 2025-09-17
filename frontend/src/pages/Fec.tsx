// pages/Fec.tsx
import { useState } from 'react'
import { api } from '../api/client'
import { useApp } from '../context/AppContext'

export default function FecPage() {
  const { exerciceId } = useApp()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const downloadFec = async () => {
    if (!exerciceId) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.get(`/api/exercices/${exerciceId}/fec`, {
        validateStatus: () => true, // on gère nous-mêmes les erreurs HTTP
      })

      // Si l’API renvoie une erreur (ex: 404/500), le corps est du JSON {detail: "..."}
      if (res.status >= 400) {
        try {
          const text = await (res.data as Blob).text()
          // tente JSON
          let msg = text
          try {
            const json = JSON.parse(text)
            if (json?.detail) msg = String(json.detail)
          } catch { /* ignore JSON parse error */ }
          setError(msg || `Erreur HTTP ${res.status}`)
        } catch {
          setError(`Erreur HTTP ${res.status}`)
        }
        return
      }

      alert(`Fichier enregistré: ${res.data.saved_to}`)
    } catch (e: any) {
      setError(e?.message || 'Erreur inconnue lors du téléchargement du FEC')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">FEC</h1>

      {!exerciceId && (
        <div className="text-sm text-gray-600">
          Sélectionnez d’abord un <span className="font-medium">client</span> et un <span className="font-medium">exercice</span> pour activer l’export FEC.
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          className="border px-3 py-1 rounded disabled:opacity-60"
          onClick={downloadFec}
          disabled={!exerciceId || loading}
        >
          {loading ? 'Génération…' : 'Télécharger le FEC (ZIP)'}
        </button>
      </div>

      {error && (
        <div className="border border-red-300 bg-red-50 text-red-800 px-3 py-2 rounded">
          <div className="font-medium">Erreur</div>
          <div className="text-sm whitespace-pre-wrap">{error}</div>
        </div>
      )}

      <div className="text-xs text-gray-500">
        L’export renvoie un ZIP contenant le FEC et un fichier <em>description</em> (avec avertissements éventuels).
        Les erreurs critiques (ex: aucune écriture, erreur serveur) s’affichent ci-dessus.
      </div>
    </div>
  )
}
