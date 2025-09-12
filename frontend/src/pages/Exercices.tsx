import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useState } from 'react'
import { useApp } from '../context/AppContext'

export default function Exercices(){
  const { clientId } = useApp()
  const qc = useQueryClient()
  const exQ = useQuery({
    queryKey:['exercices', clientId],
    queryFn: async()=> clientId ? (await api.get('/api/exercices', { params: { client_id: clientId }})).data : [],
    enabled: !!clientId
  })

  const [form, setForm] = useState({ label:'', date_start:'', date_end:'', status:'OPEN' })

  const create = useMutation({
    mutationFn: async ()=> (await api.post('/api/exercices', { client_id: clientId, ...form })).data,
    onSuccess: ()=> { setForm({ label:'', date_start:'', date_end:'', status:'OPEN' }); qc.invalidateQueries({queryKey:['exercices', clientId]}) }
  })

  const update = useMutation({
    mutationFn: async (p:any)=> (await api.patch(`/api/exercices/${p.id}`, { client_id: clientId, label:p.label, date_start:p.date_start, date_end:p.date_end, status:p.status })).data,
    onSuccess: ()=> qc.invalidateQueries({queryKey:['exercices', clientId]})
  })

  const remove = useMutation({
    mutationFn: async (id:number)=> (await api.delete(`/api/exercices/${id}`)).data,
    onSuccess: ()=> qc.invalidateQueries({queryKey:['exercices', clientId]})
  })

  if(!clientId) return <div>Sélectionne d’abord un client.</div>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Exercices</h1>
      <div className="grid grid-cols-5 gap-2 max-w-4xl">
        <input className="border p-1 col-span-1" placeholder="Label" value={form.label} onChange={e=>setForm({...form, label:e.target.value})} />
        <input className="border p-1 col-span-1" type="date" value={form.date_start} onChange={e=>setForm({...form, date_start:e.target.value})} />
        <input className="border p-1 col-span-1" type="date" value={form.date_end} onChange={e=>setForm({...form, date_end:e.target.value})} />
        <select className="border p-1 col-span-1" value={form.status} onChange={e=>setForm({...form, status:e.target.value})}>
          <option value="OPEN">OPEN</option>
          <option value="CLOSED">CLOSED</option>
        </select>
        <button className="border px-3 py-1 col-span-1" onClick={()=>create.mutate()}>Ajouter</button>
      </div>

      <table className="min-w-full border text-sm">
        <thead>
          <tr>
            <th className="border p-1 text-left">Label</th>
            <th className="border p-1">Début</th>
            <th className="border p-1">Fin</th>
            <th className="border p-1">Statut</th>
            <th className="border p-1">Actions</th>
          </tr>
        </thead>
        <tbody>
          {(exQ.data||[]).map((e:any)=> (
            <tr key={e.id} className="odd:bg-gray-50">
              <td className="border p-1">
                <input className="border p-1 w-40" defaultValue={e.label} onBlur={ev=>update.mutate({...e, label: ev.target.value})} />
              </td>
              <td className="border p-1">
                <input className="border p-1" type="date" defaultValue={e.date_start} onBlur={ev=>update.mutate({...e, date_start: ev.target.value})} />
              </td>
              <td className="border p-1">
                <input className="border p-1" type="date" defaultValue={e.date_end} onBlur={ev=>update.mutate({...e, date_end: ev.target.value})} />
              </td>
              <td className="border p-1">
                <select className="border p-1" defaultValue={e.status} onBlur={ev=>update.mutate({...e, status: ev.target.value})}>
                  <option value="OPEN">OPEN</option>
                  <option value="CLOSED">CLOSED</option>
                </select>
              </td>
              <td className="border p-1 text-center">
                <button className="border px-2 py-1" onClick={()=>remove.mutate(e.id)}>Supprimer</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
