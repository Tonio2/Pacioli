import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import Balance from './pages/Balance'
import Entries from './pages/Entries'
import PiecePage from './pages/PiecePage'
import './index.css'
import Clients from './pages/Clients'
import Exercices from './pages/Exercices'
import ImportPage from './pages/Import'
import HistoryPage from './pages/History'
import ControlsPage from './pages/Centralisateur'
import FecPage from './pages/Fec'
import NewPiecePage from './pages/NewPiecePage'
import ChartPage from './pages/Chart'

const qc = new QueryClient()

const router = createBrowserRouter([
    {
        path: '/',
        element: <App />,
        children: [
            { path: '/balance', element: <Balance />, handle: { title: 'Balance' } },
            { path: '/entries', element: <Entries />, handle: { title: 'Écritures' } },
            { path: '/piece/new', element: <NewPiecePage />, handle: { title: 'Nouvelle pièce' } },
            { path: '/piece/:jnl/:piece_ref', element: <PiecePage />, handle: { title: 'Pièce' } },
            { path: '/settings/clients', element: <Clients />, handle: { title: 'Clients' } },
            { path: '/settings/exercices', element: <Exercices />, handle: { title: 'Exercices' } },
            { path: '/import', element: <ImportPage />, handle: { title: 'Import' } },
            { path: '/history', element: <HistoryPage />, handle: { title: 'Historique' } },
            { path: '/controls', element: <ControlsPage />, handle: { title: 'Journal centralisateur' } },
            { path: '/fec', element: <FecPage />, handle: { title: 'FEC' } },
            { path: '/chart', element: <ChartPage />, handle: { title: 'Plan comptable' } },
            { index: true, element: <Balance />, handle: { title: 'Balance' } },
        ]
    }
])


ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <QueryClientProvider client={qc}>
            <RouterProvider router={router} />
        </QueryClientProvider>
    </React.StrictMode>
)
