import { Outlet, useSearchParams, useMatches, type UIMatch } from 'react-router-dom'
import { AppProvider, useApp } from './context/AppContext'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo } from 'react'
import { api } from './api/client'
import logo from '../public/logo-pacioli.svg'
import { PreserveSearchNavLink } from './components/PreserveSearchNavLink'

type Handle = { title?: string }

// Petit composant qui synchronise l’URL -> contexte sur navigation (back/forward inclus)
function UrlSearchToContextSync() {
    const [searchParams] = useSearchParams();
    const { setClientId, setExerciceId } = useApp();

    useEffect(() => {
        const c = searchParams.get('client');
        const e = searchParams.get('exercice');
        setClientId(c ? Number(c) : null);
        setExerciceId(e ? Number(e) : null);
    }, [searchParams, setClientId, setExerciceId]);

    return null;
}

function Navbar() {
    const { clientId, setClientId, exerciceId, setExerciceId } = useApp()
    const [searchParams, setSearchParams] = useSearchParams()

    // MàJ des query params sans changer de page
    const updateSearchParams = (updates: Record<string, string | undefined>) => {
        const next = new URLSearchParams(searchParams);
        Object.entries(updates).forEach(([k, v]) => {
            if (v === undefined || v === '') next.delete(k);
            else next.set(k, v);
        });
        setSearchParams(next, { replace: false });
    };

    const clientsQ = useQuery({
        queryKey: ['clients'],
        queryFn: async () => (await api.get('/api/clients')).data,
    })

    const exercicesQ = useQuery({
        queryKey: ['exercices', clientId],
        queryFn: async () =>
            clientId ? (await api.get('/api/exercices', { params: { client_id: clientId } })).data : [],
        enabled: !!clientId,
    })

    // Titre dynamique
    const matches = useMatches() as UIMatch<unknown, Handle>[];
    const leaf = matches[matches.length - 1];
    const pageTitle = leaf?.handle?.title ?? 'Pacioli';

    const clientName = useMemo(
        () => (clientsQ.data ?? []).find((c: any) => c.id === clientId)?.name ?? '-',
        [clientsQ.data, clientId]
    );
    const exName = useMemo(
        () => (exercicesQ.data ?? []).find((e: any) => e.id === exerciceId)?.label ?? '-',
        [exercicesQ.data, exerciceId]
    );

    useEffect(() => {
        document.title = `${pageTitle} - ${clientName} ${exName}`;
    }, [pageTitle, clientName, exName]);

    return (
        <div className="flex gap-4 px-4 py-2 items-center border-b flex-wrap">
            <img src={logo} alt="Logo compta Pacioli" className="w-18 h-18" />
            <div className="text-xl font-bold">Pacioli</div>

            {/* Liens qui préservent automatiquement ?client=&exercice= */}
            <PreserveSearchNavLink to="/balance">Balance</PreserveSearchNavLink>
            <PreserveSearchNavLink to="/entries">Écritures</PreserveSearchNavLink>
            <PreserveSearchNavLink to="/piece/new">Saisie</PreserveSearchNavLink>
            <PreserveSearchNavLink to="/import">Import</PreserveSearchNavLink>
            <PreserveSearchNavLink to="/controls">Journal centralisateur</PreserveSearchNavLink>
            <PreserveSearchNavLink to="/history">Historique</PreserveSearchNavLink>
            <PreserveSearchNavLink to="/fec">FEC</PreserveSearchNavLink>
            <PreserveSearchNavLink to="/chart">Plan comptable</PreserveSearchNavLink>
            <PreserveSearchNavLink to="/settings/clients">Clients</PreserveSearchNavLink>
            <PreserveSearchNavLink to="/settings/exercices">Exercices</PreserveSearchNavLink>

            <div className="ml-auto flex gap-2 items-center">
                <label htmlFor="client-select">Client</label>
                <select
                    id="client-select"
                    className="border p-1"
                    value={clientId ?? ''}
                    onChange={e => {
                        const id = e.target.value ? Number(e.target.value) : null;
                        setClientId(id);
                        // reset exercice si le client change
                        setExerciceId(null);
                        updateSearchParams({ client: id ? String(id) : undefined, exercice: undefined });
                    }}
                >
                    <option value="" disabled>—</option>
                    {(clientsQ.data || []).map((c: any) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                </select>

                <label htmlFor="exercice-select">Exercice</label>
                <select
                    id="exercice-select"
                    className="border p-1"
                    value={exerciceId ?? ''}
                    onChange={e => {
                        const id = e.target.value ? Number(e.target.value) : null;
                        setExerciceId(id);
                        updateSearchParams({ exercice: id ? String(id) : undefined });
                    }}
                    disabled={!clientId}
                >
                    <option value="" disabled>—</option>
                    {(exercicesQ.data || []).map((e: any) => (
                        <option key={e.id} value={e.id}>{e.label}</option>
                    ))}
                </select>
            </div>
        </div>
    )
}

export default function App() {
    const [searchParams] = useSearchParams();

    return (
        <AppProvider
            initialClientId={searchParams.get('client') ? Number(searchParams.get('client')) : undefined}
            initialExerciceId={searchParams.get('exercice') ? Number(searchParams.get('exercice')) : undefined}
        >
            {/* Synchronise l’URL vers le contexte en continu */}
            <UrlSearchToContextSync />
            <Navbar />
            <div className="p-4">
                <Outlet />
            </div>
        </AppProvider>
    )
}
