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

interface Props {
  data: { broker: string; value: number }[];
}

const COLORS = [
  '#10b981',
  '#3b82f6',
  '#f59e0b',
  '#8b5cf6',
  '#06b6d4',
  '#f43f5e',
];

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 shadow-lg">
      <p className="text-sm font-medium text-white">{label}</p>
      <p className="text-sm text-emerald-400">{formatIDR(payload[0].value)}</p>
    </div>
  );
}

export default function BrokerAllocationBar({ data }: Props) {
  const sorted = [...data].sort((a, b) => b.value - a.value);

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500">
        No broker data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={sorted} layout="vertical" margin={{ left: 20, right: 20 }}>
        <XAxis
          type="number"
          tickFormatter={(v) => `${(v / 1_000_000).toFixed(0)}M`}
          stroke="#64748b"
          fontSize={12}
        />
        <YAxis
          type="category"
          dataKey="broker"
          width={100}
          stroke="#64748b"
          fontSize={12}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={24}>
          {sorted.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
