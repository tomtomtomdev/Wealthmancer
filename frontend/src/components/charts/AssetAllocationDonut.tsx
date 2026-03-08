'use client';

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { formatIDR } from '@/lib/formatters';

interface AssetAllocationData {
  name: string;
  value: number;
  color: string;
}

interface Props {
  data: AssetAllocationData[];
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  const total = item.payload.total || 0;
  const pct = total > 0 ? ((item.value / total) * 100).toFixed(1) : '0';
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 shadow-lg">
      <p className="text-sm font-medium text-white">{item.name}</p>
      <p className="text-sm text-slate-300">{formatIDR(item.value)}</p>
      <p className="text-xs text-slate-400">{pct}%</p>
    </div>
  );
}

export default function AssetAllocationDonut({ data }: Props) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const enriched = data.map((d) => ({ ...d, total }));

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500">
        No asset data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={enriched}
          cx="50%"
          cy="50%"
          innerRadius={70}
          outerRadius={110}
          paddingAngle={2}
          dataKey="value"
          stroke="none"
        >
          {enriched.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <text
          x="50%"
          y="46%"
          textAnchor="middle"
          dominantBaseline="middle"
          className="fill-white text-sm font-medium"
        >
          Total
        </text>
        <text
          x="50%"
          y="56%"
          textAnchor="middle"
          dominantBaseline="middle"
          className="fill-slate-300 text-xs"
        >
          {formatIDR(total)}
        </text>
      </PieChart>
    </ResponsiveContainer>
  );
}
