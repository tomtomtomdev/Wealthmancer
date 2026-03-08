'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, TrendingUp, DollarSign, BarChart3 } from 'lucide-react';
import { getConsolidatedPortfolio } from '@/lib/api';
import { formatIDR, formatPercent, cn } from '@/lib/formatters';
import HoldingsTable from '@/components/tables/HoldingsTable';

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getConsolidatedPortfolio();
        setHoldings(data?.holdings || data?.data || data || []);
      } catch (err) {
        console.error('Failed to fetch portfolio:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const totalMarketValue = holdings.reduce(
    (sum, h) => sum + (h.market_value || 0),
    0
  );
  const totalCostBasis = holdings.reduce(
    (sum, h) => sum + (h.avg_cost || 0) * (h.total_shares || 0),
    0
  );
  const totalPnl = totalMarketValue - totalCostBasis;
  const totalPnlPercent =
    totalCostBasis > 0 ? ((totalPnl / totalCostBasis) * 100) : 0;

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Portfolio</h1>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="bg-slate-900 border-slate-800">
              <CardContent className="p-6">
                <div className="animate-pulse space-y-3">
                  <div className="h-4 bg-slate-800 rounded w-1/2"></div>
                  <div className="h-8 bg-slate-800 rounded w-3/4"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-4 bg-slate-800 rounded w-1/4"></div>
              <div className="h-64 bg-slate-800/50 rounded"></div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <PieChart className="h-6 w-6 text-emerald-400" />
        <h1 className="text-2xl font-bold text-white">Portfolio</h1>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Total Market Value</p>
                <p className="text-xl font-bold text-white">
                  {formatIDR(totalMarketValue)}
                </p>
              </div>
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <DollarSign className="h-5 w-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Total Cost Basis</p>
                <p className="text-xl font-bold text-white">
                  {formatIDR(totalCostBasis)}
                </p>
              </div>
              <div className="p-2 bg-slate-700/50 rounded-lg">
                <BarChart3 className="h-5 w-5 text-slate-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">
                  Unrealized P&L
                </p>
                <p
                  className={cn(
                    'text-xl font-bold',
                    totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  )}
                >
                  {formatIDR(totalPnl)}
                </p>
                <p
                  className={cn(
                    'text-xs mt-0.5',
                    totalPnlPercent >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  )}
                >
                  {formatPercent(totalPnlPercent)}
                </p>
              </div>
              <div
                className={cn(
                  'p-2 rounded-lg',
                  totalPnl >= 0 ? 'bg-emerald-500/10' : 'bg-rose-500/10'
                )}
              >
                <TrendingUp
                  className={cn(
                    'h-5 w-5',
                    totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  )}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Number of Stocks</p>
                <p className="text-xl font-bold text-white">
                  {holdings.length}
                </p>
              </div>
              <div className="p-2 bg-violet-500/10 rounded-lg">
                <PieChart className="h-5 w-5 text-violet-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Holdings Table */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white text-lg">
            Consolidated Holdings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <HoldingsTable data={holdings} />
        </CardContent>
      </Card>
    </div>
  );
}
