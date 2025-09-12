import React, { createContext, useContext, useState } from 'react'

type Ctx = {
  clientId: number | null
  setClientId: (v: number) => void
  exerciceId: number | null
  setExerciceId: (v: number) => void
}
const AppContext = createContext<Ctx | null>(null)

export const AppProvider: React.FC<{children: React.ReactNode}> = ({children}) => {
  const [clientId, setClientId] = useState<number | null>(1)
  const [exerciceId, setExerciceId] = useState<number | null>(1)
  return <AppContext.Provider value={{clientId, setClientId, exerciceId, setExerciceId}}>{children}</AppContext.Provider>
}

export const useApp = () => {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('AppContext missing')
  return ctx
}
