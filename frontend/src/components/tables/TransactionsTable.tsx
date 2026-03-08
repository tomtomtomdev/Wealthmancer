'use client';

import { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from '@tanstack/react-table';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { formatIDR, formatDate, cn } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface Transaction {
  id: string;
  date: string;
  institution: string;
  description: string;
  category: string;
  amount: number;
  type: 'debit' | 'credit';
  balance?: number;
}

interface Props {
  data: Transaction[];
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  transfer: 'bg-blue-500/20 text-blue-400',
  salary: 'bg-emerald-500/20 text-emerald-400',
  food: 'bg-amber-500/20 text-amber-400',
  shopping: 'bg-violet-500/20 text-violet-400',
  utilities: 'bg-cyan-500/20 text-cyan-400',
  investment: 'bg-emerald-500/20 text-emerald-400',
  entertainment: 'bg-rose-500/20 text-rose-400',
  transport: 'bg-orange-500/20 text-orange-400',
  healthcare: 'bg-pink-500/20 text-pink-400',
  other: 'bg-slate-500/20 text-slate-400',
};

export default function TransactionsTable({
  data,
  page,
  totalPages,
  onPageChange,
}: Props) {
  const columns = useMemo<ColumnDef<Transaction>[]>(
    () => [
      {
        accessorKey: 'date',
        header: 'Date',
        cell: (info) => (
          <span className="text-slate-300">
            {formatDate(info.getValue() as string)}
          </span>
        ),
      },
      {
        accessorKey: 'institution',
        header: 'Institution',
        cell: (info) => (
          <span className="font-medium text-white">
            {info.getValue() as string}
          </span>
        ),
      },
      {
        accessorKey: 'description',
        header: 'Description',
        cell: (info) => (
          <span className="text-slate-300 max-w-xs truncate block">
            {info.getValue() as string}
          </span>
        ),
      },
      {
        accessorKey: 'category',
        header: 'Category',
        cell: (info) => {
          const cat = (info.getValue() as string) || 'other';
          const colorClass =
            CATEGORY_COLORS[cat.toLowerCase()] || CATEGORY_COLORS.other;
          return (
            <Badge
              variant="secondary"
              className={cn('text-xs capitalize', colorClass)}
            >
              {cat}
            </Badge>
          );
        },
      },
      {
        accessorKey: 'amount',
        header: 'Amount',
        cell: (info) => {
          const row = info.row.original;
          const isDebit = row.type === 'debit';
          return (
            <span
              className={cn(
                'font-medium',
                isDebit ? 'text-rose-400' : 'text-emerald-400'
              )}
            >
              {isDebit ? '-' : '+'}
              {formatIDR(Math.abs(info.getValue() as number))}
            </span>
          );
        },
      },
      {
        accessorKey: 'balance',
        header: 'Balance',
        cell: (info) => {
          const val = info.getValue() as number | undefined;
          return val !== undefined ? (
            <span className="text-slate-400">{formatIDR(val)}</span>
          ) : (
            <span className="text-slate-600">-</span>
          );
        },
      },
    ],
    []
  );

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (!data.length) {
    return (
      <div className="text-center py-12 text-slate-500">
        No transactions found
      </div>
    );
  }

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-slate-800 bg-slate-900/50">
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="text-left px-4 py-3 text-slate-400 font-medium"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4">
        <p className="text-sm text-slate-500">
          Page {page} of {totalPages}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
