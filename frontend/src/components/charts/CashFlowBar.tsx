'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { formatIDR } from '@/lib/formatters';

interface Props {
  data: { month: string; income: number; expense: number }[];
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 shadow-lg">
      <p className="text-sm font-medium text-white mb-1">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} className="text-sm" style={{ color: p.color }}>
          {p.name}: {formatIDR(p.value)}
        </p>
      ))}
    </div>
  );
}

export default function CashFlowBar({ data }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500">
        No cash flow data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ left: 10, right: 10 }}>
        <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
        <YAxis
          tickFormatter={(v) => `${(v / 1_000_000).toFixed(0)}M`}
          stroke="#64748b"
          fontSize={12}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }}
        />
        <Bar
          dataKey="income"
          name="Income"
          fill="#10b981"
          radius={[4, 4, 0, 0]}
          barSize={20}
        />
        <Bar
          dataKey="expense"
          name="Expense"
          fill="#f43f5e"
          radius={[4, 4, 0, 0]}
          barSize={20}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
