'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { formatIDR } from '@/lib/formatters';

interface HoldingData {
  ticker: string;
  market_value: number;
  unrealized_pnl: number;
}

interface Props {
  data: HoldingData[];
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const item = payload[0]?.payload;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 shadow-lg">
      <p className="text-sm font-medium text-white">{label}</p>
      <p className="text-sm text-slate-300">
        Market Value: {formatIDR(item?.market_value || 0)}
      </p>
      <p
        className={`text-sm ${
          (item?.unrealized_pnl || 0) >= 0
            ? 'text-emerald-400'
            : 'text-rose-400'
        }`}
      >
        P&L: {formatIDR(item?.unrealized_pnl || 0)}
      </p>
    </div>
  );
}

export default function TopHoldingsBar({ data }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500">
        No holdings data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ left: 10, right: 20 }}
      >
        <XAxis
          type="number"
          tickFormatter={(v) => `${(v / 1_000_000).toFixed(0)}M`}
          stroke="#64748b"
          fontSize={12}
        />
        <YAxis
          type="category"
          dataKey="ticker"
          width={70}
          stroke="#64748b"
          fontSize={12}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="market_value" radius={[0, 4, 4, 0]} barSize={20}>
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.unrealized_pnl >= 0 ? '#10b981' : '#f43f5e'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
