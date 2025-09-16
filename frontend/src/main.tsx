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
import ControlsPage from './pages/Controls'
import FecPage from './pages/Fec'
import NewPiecePage from './pages/NewPiecePage'
import ChartPage from './pages/Chart'

const qc = new QueryClient()

const router = createBrowserRouter([
    {
        path: '/', element: <App />, children: [
            { path: '/balance', element: <Balance /> },
            { path: '/entries', element: <Entries /> },
            { path: '/piece/new', element: <NewPiecePage /> },
            { path: '/piece/:jnl/:piece_ref', element: <PiecePage /> },
            { path: '/settings/clients', element: <Clients /> },
            { path: '/settings/exercices', element: <Exercices /> },
            { path: '/import', element: <ImportPage /> },
            { path: '/history', element: <HistoryPage /> },
            { path: '/controls', element: <ControlsPage /> },
            { path: '/fec', element: <FecPage /> },
            { path: '/chart', element: <ChartPage /> },
            { index: true, element: <Balance /> },
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
