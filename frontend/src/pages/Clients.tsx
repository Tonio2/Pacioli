import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useState } from 'react'

export default function Clients(){
  const qc = useQueryClient()
  const clientsQ = useQuery({ queryKey:['clients'], queryFn: async()=> (await api.get('/api/clients')).data })

  const [name, setName] = useState('')

  const create = useMutation({
    mutationFn: async ()=> (await api.post('/api/clients', { name })).data,
    onSuccess: ()=> { setName(''); qc.invalidateQueries({queryKey:['clients']}) }
  })

  const update = useMutation({
    mutationFn: async (p:{id:number, name:string})=> (await api.patch(`/api/clients/${p.id}`, { name: p.name })).data,
    onSuccess: ()=> qc.invalidateQueries({queryKey:['clients']})
  })

  const remove = useMutation({
    mutationFn: async (id:number)=> (await api.delete(`/api/clients/${id}`)).data,
    onSuccess: ()=> qc.invalidateQueries({queryKey:['clients']})
  })

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Clients</h1>
      <div className="flex gap-2">
        <input className="border p-1" placeholder="Nom" value={name} onChange={e=>setName(e.target.value)} />
        <button className="border px-3 py-1" onClick={()=>create.mutate()}>Ajouter</button>
      </div>
      <table className="min-w-full border text-sm">
        <thead><tr><th className="border p-1 text-left">Nom</th><th className="border p-1">Actions</th></tr></thead>
        <tbody>
          {(clientsQ.data||[]).map((c:any)=> (
            <tr key={c.id} className="odd:bg-gray-50">
              <td className="border p-1">
                <input className="border p-1 w-full" defaultValue={c.name} onBlur={e=>update.mutate({id:c.id, name:e.target.value})} />
              </td>
              <td className="border p-1 text-center">
                <button className="border px-2 py-1" onClick={()=>remove.mutate(c.id)}>Supprimer</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
