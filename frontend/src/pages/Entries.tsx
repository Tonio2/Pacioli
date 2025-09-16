import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { type ColumnDef, createColumnHelper, flexRender } from '@tanstack/react-table'
import { useApp } from '../context/AppContext'
import { useSearchParams, Link } from 'react-router-dom'
import { useVirtualizer } from '@tanstack/react-virtual'
import { fmtCents } from '../modules/utils/amount'

type Row = {
    id: number; date: string; jnl: string; piece_ref: string;
    account_id: number; accnum: string; acclib: string;
    lib: string; debit_minor: number; credit_minor: number
}

type Page = { rows: Row[]; page_info: { next?: string | null; prev?: string | null; has_next: boolean; has_prev: boolean } }

export default function Entries() {
    const { exerciceId } = useApp()
    const [sp, setSp] = useSearchParams()
    const params = Object.fromEntries(sp.entries())

    // --- filtres contrôlés ---
    const [journal, setJournal] = useState<string>(params.journal ?? '')
    const [pieceRef, setPieceRef] = useState<string>(params.piece_ref ?? '')
    const [compte, setCompte] = useState<string>(params.compte ?? '')
    const [minDate, setMinDate] = useState<string>(params.min_date ?? '')
    const [maxDate, setMaxDate] = useState<string>(params.max_date ?? '')
    const [minAmt, setMinAmt] = useState<string>(params.min_amt ?? '')
    const [maxAmt, setMaxAmt] = useState<string>(params.max_amt ?? '')
    const [search, setSearch] = useState<string>(params.search ?? '')
    const [sort, setSort] = useState<string>(params.sort ?? 'date,id')

    const dJournal = useDebounced(journal)
    const dPieceRef = useDebounced(pieceRef)
    const dCompte = useDebounced(compte)
    const dMinDate = useDebounced(minDate)
    const dMaxDate = useDebounced(maxDate)
    const dMinAmt = useDebounced(minAmt)
    const dMaxAmt = useDebounced(maxAmt)
    const dSearch = useDebounced(search)
    const dSort = useDebounced(sort, 0) // pas besoin ici, mais OK


    function useDebounced<T>(value: T, delay = 300) {
        const [deb, setDeb] = useState(value)
        useEffect(() => {
            const id = setTimeout(() => setDeb(value), delay)
            return () => clearTimeout(id)
        }, [value, delay])
        return deb
    }


    // suggest pièce
    const { data: suggest } = useQuery({
        queryKey: ['entries-suggest-piece', exerciceId, pieceRef],
        queryFn: async () => (await api.get('/api/entries/suggest-piece', { params: { exercice_id: exerciceId, q: pieceRef } })).data,
        enabled: !!exerciceId && pieceRef.length >= 2
    })

    const pageSize = 150

    const queryParams = useMemo(() => ({
        exercice_id: exerciceId,
        journal: dJournal || undefined,
        piece_ref: dPieceRef || undefined,
        compte: dCompte || undefined,
        min_date: dMinDate || undefined,
        max_date: dMaxDate || undefined,
        min_amt: dMinAmt ? Number(dMinAmt) : undefined,
        max_amt: dMaxAmt ? Number(dMaxAmt) : undefined,
        search: dSearch || undefined,
        sort: dSort,
        page_size: pageSize,
    }), [exerciceId, dJournal, dPieceRef, dCompte, dMinDate, dMaxDate, dMinAmt, dMaxAmt, dSearch, dSort])


    // infini: after token
    const { data, fetchNextPage, hasNextPage, isFetching } = useInfiniteQuery<Page>({
        queryKey: ['entries', queryParams],
        initialPageParam: undefined,
        queryFn: async ({ pageParam }) => {
            const res = await api.get('/api/entries', { params: { ...queryParams, after: pageParam ?? undefined } })
            return res.data
        },
        getNextPageParam: (lastPage) => lastPage?.page_info?.has_next ? lastPage.page_info.next : undefined,
        enabled: !!exerciceId,
        staleTime: 30_000,
    })

    const rows: Row[] = (data?.pages ?? []).flatMap(p => p.rows)

    // Virtualizer
    const parentRef = useRef<HTMLDivElement | null>(null)
    const rowVirtualizer = useVirtualizer({
        count: rows.length + (hasNextPage ? 1 : 0),
        getScrollElement: () => parentRef.current,
        estimateSize: () => 36, // hauteur ligne approx
        overscan: 10,
    })

    // Auto fetch quand on approche du bas
    const virtualItems = rowVirtualizer.getVirtualItems()
    const lastItem = virtualItems[virtualItems.length - 1]
    if (lastItem && lastItem.index >= rows.length - 1 && hasNextPage && !isFetching) {
        // déclenche la suite
        fetchNextPage()
    }

    const paddingTop = virtualItems.length ? virtualItems[0].start : 0
    const paddingBottom = virtualItems.length
        ? rowVirtualizer.getTotalSize() - virtualItems[virtualItems.length - 1].end
        : 0

    useEffect(() => {
        const last = virtualItems[virtualItems.length - 1]
        if (!isFetching && hasNextPage && last && last.index >= rows.length - 1) {
            fetchNextPage()
        }
    }, [virtualItems, isFetching, hasNextPage, rows.length, fetchNextPage])

    // colonnes triables (on délègue au serveur)
    const ch = createColumnHelper<Row>()
    const mkSortableHeader = (label: string, key: string) => (
        <button
            className="underline"
            onClick={() => {
                setSort(prev => {
                    const cur = prev.split(',')[0] || 'date'
                    const isDesc = cur.startsWith('-')
                    const base = cur.replace(/^-/, '')
                    return base === key ? (isDesc ? key : `-${key}`) + ',id' : key + ',id'
                })
            }}
            title="Trier"
        >
            {label}{sort.replace(',id', '') === key ? ' ▲' : (sort.replace(',id', '') === `-${key}` ? ' ▼' : '')}
        </button>
    )


    const columns: ColumnDef<Row, any>[] = [
        ch.accessor('date', { header: () => mkSortableHeader('Date', 'date') }),
        ch.accessor('jnl', { header: () => mkSortableHeader('Jnl', 'jnl') }),
        ch.accessor('piece_ref', {
            header: () => mkSortableHeader('Pièce', 'piece_ref'),
            cell: i => <Link className="underline" to={`/piece/${i.row.original.jnl}/${i.row.original.piece_ref}`}>{i.getValue<string>()}</Link>
        }),
        ch.accessor('accnum', { header: () => mkSortableHeader('Compte', 'accnum') }),
        ch.accessor('lib', { header: 'Libellé' }),
        ch.accessor('debit_minor', { header: () => mkSortableHeader('Débit', 'debit_minor') }),
        ch.accessor('credit_minor', { header: () => mkSortableHeader('Crédit', 'credit_minor') }),
    ]

    // Export CSV
    const onExport = useCallback(() => {
        const p = new URLSearchParams()
        Object.entries(queryParams).forEach(([k, v]) => {
            if (v !== undefined && v !== null && v !== '') p.append(k, String(v))
        })
        window.location.href = `/api/entries/export?${p.toString()}`
    }, [queryParams])

    useEffect(() => {
        const next = new URLSearchParams()
        if (dJournal) next.set('journal', dJournal)
        if (dPieceRef) next.set('piece_ref', dPieceRef)
        if (dCompte) next.set('compte', dCompte)
        if (dMinDate) next.set('min_date', dMinDate)
        if (dMaxDate) next.set('max_date', dMaxDate)
        if (dMinAmt) next.set('min_amt', dMinAmt)
        if (dMaxAmt) next.set('max_amt', dMaxAmt)
        if (dSearch) next.set('search', dSearch)
        next.set('sort', dSort)
        setSp(next, { replace: true })
    }, [dJournal, dPieceRef, dCompte, dMinDate, dMaxDate, dMinAmt, dMaxAmt, dSearch, dSort, setSp])


    const COLS = useMemo(
        () => ([
            <col key="date" style={{ width: '8rem' }} />,   // Date
            <col key="jnl" style={{ width: '4.5rem' }} />, // Jnl
            <col key="piece" style={{ width: '12rem' }} />,  // Pièce
            <col key="acc" style={{ width: '8rem' }} />,   // Compte
            <col key="lib" />,                             // Libellé (auto)
            <col key="debit" style={{ width: '8rem' }} />,   // Débit
            <col key="credit" style={{ width: '8rem' }} />,   // Crédit
        ]),
        []
    )


    return (
        <div className="space-y-3">
            <h1 className="text-xl font-semibold">Écritures</h1>

            <form className="grid grid-cols-2 md:grid-cols-4 gap-2 items-end">
                <div>
                    <label className="text-xs">Journal</label>
                    <input value={journal} onChange={e => setJournal(e.target.value)} className="border px-2 py-1 w-full" />
                </div>
                <div>
                    <label className="text-xs">Pièce</label>
                    <input list="pieces" value={pieceRef} onChange={e => setPieceRef(e.target.value)} className="border px-2 py-1 w-full" />
                    <datalist id="pieces">
                        {(suggest?.items ?? []).map((it: string) => <option value={it} key={it} />)}
                    </datalist>
                </div>
                <div>
                    <label className="text-xs">Compte</label>
                    <input value={compte} onChange={e => setCompte(e.target.value)} className="border px-2 py-1 w-full" />
                </div>
                <div className="flex gap-2">
                    <div className="flex-1">
                        <label className="text-xs">Du</label>
                        <input type="date" value={minDate} onChange={e => setMinDate(e.target.value)} className="border px-2 py-1 w-full" />
                    </div>
                    <div className="flex-1">
                        <label className="text-xs">Au</label>
                        <input type="date" value={maxDate} onChange={e => setMaxDate(e.target.value)} className="border px-2 py-1 w-full" />
                    </div>
                </div>
                <div className="flex gap-2">
                    <div className="flex-1">
                        <label className="text-xs">Min Δ</label>
                        <input value={minAmt} onChange={e => setMinAmt(e.target.value)} className="border px-2 py-1 w-full" placeholder="0.00" />
                    </div>
                    <div className="flex-1">
                        <label className="text-xs">Max Δ</label>
                        <input value={maxAmt} onChange={e => setMaxAmt(e.target.value)} className="border px-2 py-1 w-full" placeholder="0.00" />
                    </div>
                </div>
                <div>
                    <label className="text-xs">Recherche libellé</label>
                    <input value={search} onChange={e => setSearch(e.target.value)} className="border px-2 py-1 w-full" />
                </div>
                <div className="flex gap-2">
                    <button type="button" onClick={onExport} className="px-3 py-1 border rounded">Export CSV</button>
                </div>
            </form>

            <div ref={parentRef} className="h-[70vh] overflow-auto border rounded">
                <table className="min-w-full table-fixed border-separate border-spacing-0 text-sm border [font-variant-numeric:tabular-nums]">
                    {[
                        <colgroup key="cg">{COLS}</colgroup>,

                        <thead key="h" className="sticky top-0 bg-white z-20 shadow-[0_1px_0_0_rgba(0,0,0,0.12)]">
                            <tr>
                                {columns.map((col, i) => (
                                    <th key={i} className="px-2 py-1 text-left">
                                        {flexRender(col.header as any, { column: { columnDef: col } } as any)}
                                    </th>
                                ))}
                            </tr>
                        </thead>,

                        <tbody key="b">
                            {[
                                ...(paddingTop > 0
                                    ? [<tr key="pad-top"><td colSpan={columns.length} className="border-t" style={{ height: paddingTop }} /></tr>]
                                    : []),

                                ...virtualItems.map((vi) => {
                                    const isLoader = vi.index > rows.length - 1
                                    if (isLoader) {
                                        return (
                                            <tr key="loader">
                                                <td colSpan={columns.length} className="px-2 py-2 text-center border-t">
                                                    {hasNextPage ? 'Chargement…' : '—'}
                                                </td>
                                            </tr>
                                        )
                                    }
                                    const row = rows[vi.index]
                                    return (
                                        <tr key={row.id} className={vi.index % 2 === 1 ? 'bg-gray-50' : undefined}>
                                            <td className="border px-2 py-1">{row.date}</td>
                                            <td className="border px-2 py-1">{row.jnl}</td>
                                            <td className="border px-2 py-1">
                                                <Link className="underline" to={`/piece/${row.jnl}/${row.piece_ref}`}>{row.piece_ref}</Link>
                                            </td>
                                            <td className="border px-2 py-1">{row.accnum}</td>
                                            <td className="border px-2 py-1">{row.lib}</td>
                                            <td className="border px-2 py-1 text-right">{fmtCents(row.debit_minor)}</td>
                                            <td className="border px-2 py-1 text-right">{fmtCents(row.credit_minor)}</td>
                                        </tr>
                                    )
                                }),

                                ...(paddingBottom > 0
                                    ? [<tr key="pad-bottom"><td colSpan={columns.length} style={{ height: paddingBottom }} /></tr>]
                                    : []),
                            ]}
                        </tbody>,
                    ]}
                </table>
            </div>



        </div>
    )
}
