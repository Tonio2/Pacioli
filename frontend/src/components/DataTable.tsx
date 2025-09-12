import { useReactTable, getCoreRowModel, flexRender, type ColumnDef } from '@tanstack/react-table'

type Props<T> = { data: T[]; columns: ColumnDef<T, any>[] }
export default function DataTable<T extends object>({ data, columns }: Props<T>){
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() })
  return (
    <table className="min-w-full border text-sm">
      <thead>
        {table.getHeaderGroups().map(hg=> (
          <tr key={hg.id}>
            {hg.headers.map(h => (
              <th key={h.id} className="border px-2 py-1 text-left">
                {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map(r=> (
          <tr key={r.id} className="odd:bg-gray-50">
            {r.getVisibleCells().map(c => (
              <td key={c.id} className="border px-2 py-1">{flexRender(c.column.columnDef.cell, c.getContext())}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
