'use client';

import { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getExpandedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ExpandedState,
} from '@tanstack/react-table';
import { ChevronDown, ChevronRight, Download, ArrowUpDown } from 'lucide-react';
import { formatIDR, formatPercent, cn } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface BrokerDetail {
  broker: string;
  shares: number;
  avg_cost: number;
  market_value: number;
  unrealized_pnl: number;
  pnl_percent: number;
}

interface Holding {
  stock: string;
  total_shares: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  pnl_percent: number;
  portfolio_percent: number;
  brokers: string[];
  broker_details?: BrokerDetail[];
}

interface Props {
  data: Holding[];
}

export default function HoldingsTable({ data }: Props) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [expanded, setExpanded] = useState<ExpandedState>({});

  const columns = useMemo<ColumnDef<Holding>[]>(
    () => [
      {
        id: 'expander',
        header: () => null,
        cell: ({ row }) =>
          row.original.broker_details?.length ? (
            <button
              onClick={row.getToggleExpandedHandler()}
              className="p-1 hover:bg-slate-700 rounded"
            >
              {row.getIsExpanded() ? (
                <ChevronDown className="h-4 w-4 text-slate-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-slate-400" />
              )}
            </button>
          ) : null,
        size: 40,
      },
      {
        accessorKey: 'stock',
        header: 'Stock',
        cell: (info) => (
          <span className="font-medium text-white">
            {info.getValue() as string}
          </span>
        ),
      },
      {
        accessorKey: 'total_shares',
        header: 'Shares',
        cell: (info) => (info.getValue() as number).toLocaleString('id-ID'),
      },
      {
        accessorKey: 'avg_cost',
        header: 'Avg Cost',
        cell: (info) => formatIDR(info.getValue() as number),
      },
      {
        accessorKey: 'current_price',
        header: 'Price',
        cell: (info) => formatIDR(info.getValue() as number),
      },
      {
        accessorKey: 'market_value',
        header: 'Market Value',
        cell: (info) => (
          <span className="font-medium">
            {formatIDR(info.getValue() as number)}
          </span>
        ),
      },
      {
        accessorKey: 'unrealized_pnl',
        header: 'Unrealized P&L',
        cell: (info) => {
          const val = info.getValue() as number;
          return (
            <span
              className={cn(
                'font-medium',
                val >= 0 ? 'text-emerald-400' : 'text-rose-400'
              )}
            >
              {formatIDR(val)}
            </span>
          );
        },
      },
      {
        accessorKey: 'pnl_percent',
        header: '% P&L',
        cell: (info) => {
          const val = info.getValue() as number;
          return (
            <span
              className={cn(
                'font-medium',
                val >= 0 ? 'text-emerald-400' : 'text-rose-400'
              )}
            >
              {formatPercent(val)}
            </span>
          );
        },
      },
      {
        accessorKey: 'portfolio_percent',
        header: '% Portfolio',
        cell: (info) => `${(info.getValue() as number).toFixed(1)}%`,
      },
      {
        accessorKey: 'brokers',
        header: 'Brokers',
        cell: (info) => (
          <div className="flex flex-wrap gap-1">
            {(info.getValue() as string[]).map((b) => (
              <Badge
                key={b}
                variant="secondary"
                className="bg-slate-700 text-slate-300 text-xs"
              >
                {b}
              </Badge>
            ))}
          </div>
        ),
        enableSorting: false,
      },
    ],
    []
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, expanded },
    onSortingChange: setSorting,
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowCanExpand: (row) => !!(row.original.broker_details?.length),
  });

  function exportCSV() {
    const headers = [
      'Stock',
      'Shares',
      'Avg Cost',
      'Current Price',
      'Market Value',
      'Unrealized P&L',
      '% P&L',
      '% Portfolio',
      'Brokers',
    ];
    const rows = data.map((h) => [
      h.stock,
      h.total_shares,
      h.avg_cost,
      h.current_price,
      h.market_value,
      h.unrealized_pnl,
      h.pnl_percent,
      h.portfolio_percent,
      h.brokers.join('; '),
    ]);
    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'portfolio.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!data.length) {
    return (
      <div className="text-center py-12 text-slate-500">
        No holdings data available
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-end mb-4">
        <Button
          variant="outline"
          size="sm"
          onClick={exportCSV}
          className="border-slate-700 text-slate-300 hover:bg-slate-800"
        >
          <Download className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-slate-800 bg-slate-900/50">
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="text-left px-4 py-3 text-slate-400 font-medium cursor-pointer select-none"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <div className="flex items-center gap-1">
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                      {header.column.getCanSort() && (
                        <ArrowUpDown className="h-3 w-3 text-slate-500" />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <>
                <tr
                  key={row.id}
                  className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3 text-slate-300">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </td>
                  ))}
                </tr>
                {row.getIsExpanded() &&
                  row.original.broker_details?.map((detail) => (
                    <tr
                      key={`${row.id}-${detail.broker}`}
                      className="bg-slate-900/80 border-b border-slate-800/30"
                    >
                      <td className="px-4 py-2"></td>
                      <td className="px-4 py-2 text-slate-500 text-xs">
                        {detail.broker}
                      </td>
                      <td className="px-4 py-2 text-slate-400 text-xs">
                        {detail.shares.toLocaleString('id-ID')}
                      </td>
                      <td className="px-4 py-2 text-slate-400 text-xs">
                        {formatIDR(detail.avg_cost)}
                      </td>
                      <td className="px-4 py-2 text-slate-400 text-xs">-</td>
                      <td className="px-4 py-2 text-slate-400 text-xs">
                        {formatIDR(detail.market_value)}
                      </td>
                      <td
                        className={cn(
                          'px-4 py-2 text-xs font-medium',
                          detail.unrealized_pnl >= 0
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        )}
                      >
                        {formatIDR(detail.unrealized_pnl)}
                      </td>
                      <td
                        className={cn(
                          'px-4 py-2 text-xs font-medium',
                          detail.pnl_percent >= 0
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        )}
                      >
                        {formatPercent(detail.pnl_percent)}
                      </td>
                      <td className="px-4 py-2 text-slate-400 text-xs">-</td>
                      <td className="px-4 py-2">
                        <Badge
                          variant="secondary"
                          className="bg-slate-700 text-slate-400 text-xs"
                        >
                          {detail.broker}
                        </Badge>
                      </td>
                    </tr>
                  ))}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
