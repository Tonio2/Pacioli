import React, { createContext, useContext, useEffect, useState } from 'react'

type Ctx = {
    clientId: number | null
    setClientId: (v: number | null) => void
    exerciceId: number | null
    setExerciceId: (v: number | null) => void
}
const AppContext = createContext<Ctx | null>(null)

type ProviderProps = {
    children: React.ReactNode
    initialClientId?: number
    initialExerciceId?: number
}

export const AppProvider: React.FC<ProviderProps> = ({ children, initialClientId, initialExerciceId }) => {
    const lsClient = typeof window !== 'undefined' ? window.localStorage.getItem('clientId') : null
    const lsExo = typeof window !== 'undefined' ? window.localStorage.getItem('exerciceId') : null

    const [clientId, setClientId] = useState<number | null>(
        initialClientId ?? (lsClient ? Number(lsClient) : null)
    )
    const [exerciceId, setExerciceId] = useState<number | null>(
        initialExerciceId ?? (lsExo ? Number(lsExo) : null)
    )

    useEffect(() => {
        if (clientId != null) localStorage.setItem('clientId', String(clientId))
        else localStorage.removeItem('clientId')
    }, [clientId])

    useEffect(() => {
        if (exerciceId != null) localStorage.setItem('exerciceId', String(exerciceId))
        else localStorage.removeItem('exerciceId')
    }, [exerciceId])

    return (
        <AppContext.Provider value={{ clientId, setClientId, exerciceId, setExerciceId }}>
            {children}
        </AppContext.Provider>
    )
}

export const useApp = () => {
    const ctx = useContext(AppContext)
    if (!ctx) throw new Error('AppContext missing')
    return ctx
}
