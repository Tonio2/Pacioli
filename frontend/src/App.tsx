import { Outlet, Link, useNavigate } from 'react-router-dom'
import { AppProvider, useApp } from './context/AppContext'
import { useQuery } from '@tanstack/react-query'
import { api } from './api/client'

import logo from '../public/logo-pacioli.svg'


function Navbar() {
    const { clientId, setClientId, exerciceId, setExerciceId } = useApp()
    const nav = useNavigate()

    const clientsQ = useQuery({ queryKey: ['clients'], queryFn: async () => (await api.get('/api/clients')).data })
    const exercicesQ = useQuery({
        queryKey: ['exercices', clientId],
        queryFn: async () => clientId ? (await api.get('/api/exercices', { params: { client_id: clientId } })).data : [],
        enabled: !!clientId
    })

    return (
        <div className="flex gap-4 px-4 py-2 items-center border-b flex-wrap">
            <img src={logo} alt="Logo compta" className="w-18 h-18" />
            <div className="text-xl font-bold">Pacioli</div>
            <Link to="/balance" className="underline">Balance</Link>
            <Link to="/entries" className="underline">Écritures</Link>
            <Link to="/piece/new" className='underline'>Saisie</Link>
            <Link to="/import" className="underline">Import</Link>
            <Link to="/controls" className="underline">Journal centralisateur</Link>
            <Link to="/history" className="underline">Historique</Link>
            <Link to="/fec" className="underline">FEC</Link>
            <Link to="/chart" className="underline">Plan comptable</Link>
            <Link to="/settings/clients" className="underline">Clients</Link>
            <Link to="/settings/exercices" className="underline">Exercices</Link>
            <div className="ml-auto flex gap-2 items-center">
                <label>Client</label>
                <select className="border p-1" value={clientId ?? ''} onChange={e => { const id = Number(e.target.value); setClientId(id); nav('/balance') }}>
                    <option value="" disabled>—</option>
                    {(clientsQ.data || []).map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <label>Exercice</label>
                <select className="border p-1" value={exerciceId ?? ''} onChange={e => { setExerciceId(Number(e.target.value)); nav('/balance') }}>
                    <option value="" disabled>—</option>
                    {(exercicesQ.data || []).map((e: any) => <option key={e.id} value={e.id}>{e.label}</option>)}
                </select>
            </div>
        </div>
    )
}

export default function App() {
    return (
        <AppProvider>
            <Navbar />
            <div className="p-4">
                <Outlet />
            </div>
        </AppProvider>
    )
}
