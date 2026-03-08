'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Wallet, DollarSign } from 'lucide-react';
import {
  getDashboardSummary,
  getCashFlow,
  getConsolidatedPortfolio,
  getPortfolioByBroker,
  getTransactions,
} from '@/lib/api';
import { formatIDR, formatDate, cn } from '@/lib/formatters';
import AssetAllocationDonut from '@/components/charts/AssetAllocationDonut';
import BrokerAllocationBar from '@/components/charts/BrokerAllocationBar';
import CashFlowBar from '@/components/charts/CashFlowBar';
import TopHoldingsBar from '@/components/charts/TopHoldingsBar';

function SkeletonCard() {
  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardContent className="p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-slate-800 rounded w-1/3"></div>
          <div className="h-8 bg-slate-800 rounded w-2/3"></div>
        </div>
      </CardContent>
    </Card>
  );
}

function SkeletonChart() {
  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardContent className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-slate-800 rounded w-1/3"></div>
          <div className="h-64 bg-slate-800/50 rounded"></div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<any>(null);
  const [cashFlow, setCashFlow] = useState<any[]>([]);
  const [portfolio, setPortfolio] = useState<any[]>([]);
  const [brokers, setBrokers] = useState<any[]>([]);
  const [recentTx, setRecentTx] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [summaryData, cashFlowData, portfolioData, brokerData, txData] =
          await Promise.allSettled([
            getDashboardSummary(),
            getCashFlow(),
            getConsolidatedPortfolio(),
            getPortfolioByBroker(),
            getTransactions({ page: 1, limit: 10 }),
          ]);

        if (summaryData.status === 'fulfilled') setSummary(summaryData.value);
        if (cashFlowData.status === 'fulfilled')
          setCashFlow(cashFlowData.value?.data || cashFlowData.value || []);
        if (portfolioData.status === 'fulfilled')
          setPortfolio(
            portfolioData.value?.holdings || portfolioData.value?.data || portfolioData.value || []
          );
        if (brokerData.status === 'fulfilled')
          setBrokers(brokerData.value?.data || brokerData.value || []);
        if (txData.status === 'fulfilled')
          setRecentTx(
            txData.value?.transactions || txData.value?.data || txData.value || []
          );
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const CHART_COLORS = [
    '#10b981',
    '#3b82f6',
    '#f59e0b',
    '#8b5cf6',
    '#06b6d4',
    '#f43f5e',
  ];

  const assetAllocation = summary?.asset_allocation
    ? (Array.isArray(summary.asset_allocation)
        ? summary.asset_allocation.map((a: any, i: number) => ({
            name: a.name || a.type || a.category,
            value: a.value || a.amount,
            color: CHART_COLORS[i % CHART_COLORS.length],
          }))
        : Object.entries(summary.asset_allocation).map(([key, val], i) => ({
            name: key,
            value: Number(val),
            color: CHART_COLORS[i % CHART_COLORS.length],
          })))
    : [];

  const brokerAllocation = summary?.broker_allocation
    ? (Array.isArray(summary.broker_allocation)
        ? summary.broker_allocation.map((b: any) => ({
            broker: b.broker || b.name || b.institution,
            value: b.value || b.total_value || b.market_value || 0,
          }))
        : Object.entries(summary.broker_allocation).map(([key, val]) => ({
            broker: key,
            value: Number(val),
          })))
    : (Array.isArray(brokers)
        ? brokers.map((b: any) => ({
            broker: b.broker || b.name || b.institution,
            value: b.value || b.total_value || b.market_value || 0,
          }))
        : []);

  const topHoldings = [...portfolio]
    .sort((a, b) => (b.market_value || 0) - (a.market_value || 0))
    .slice(0, 10)
    .map((h) => ({
      ticker: h.stock || h.ticker || h.symbol,
      market_value: h.market_value || 0,
      unrealized_pnl: h.unrealized_pnl || 0,
    }));

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonChart />
          <SkeletonChart />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonChart />
          <SkeletonChart />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      {/* Row 1: Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Net Worth</p>
                <p
                  className={cn(
                    'text-2xl font-bold',
                    (summary?.net_worth || 0) >= 0
                      ? 'text-emerald-400'
                      : 'text-rose-400'
                  )}
                >
                  {formatIDR(summary?.net_worth || 0)}
                </p>
              </div>
              <div className="p-3 bg-emerald-500/10 rounded-lg">
                <Wallet className="h-6 w-6 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Total Assets</p>
                <p className="text-2xl font-bold text-white">
                  {formatIDR(summary?.total_assets || 0)}
                </p>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-lg">
                <TrendingUp className="h-6 w-6 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Total Liabilities</p>
                <p className="text-2xl font-bold text-rose-400">
                  {formatIDR(summary?.total_liabilities || 0)}
                </p>
              </div>
              <div className="p-3 bg-rose-500/10 rounded-lg">
                <TrendingDown className="h-6 w-6 text-rose-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 2: Asset Allocation & Broker Allocation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white text-lg">
              Asset Allocation
            </CardTitle>
          </CardHeader>
          <CardContent>
            {assetAllocation.length > 0 ? (
              <>
                <AssetAllocationDonut data={assetAllocation} />
                <div className="flex flex-wrap gap-4 mt-4 justify-center">
                  {assetAllocation.map((item: any) => (
                    <div key={item.name} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-xs text-slate-400">{item.name}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-64 text-slate-500">
                No asset allocation data
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white text-lg">
              Broker Allocation
            </CardTitle>
          </CardHeader>
          <CardContent>
            {brokerAllocation.length > 0 ? (
              <BrokerAllocationBar data={brokerAllocation} />
            ) : (
              <div className="flex items-center justify-center h-64 text-slate-500">
                No broker data
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 3: Top Holdings & Cash Flow */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white text-lg">
              Top Holdings
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topHoldings.length > 0 ? (
              <TopHoldingsBar data={topHoldings} />
            ) : (
              <div className="flex items-center justify-center h-64 text-slate-500">
                No holdings data
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white text-lg">
              Monthly Cash Flow
            </CardTitle>
          </CardHeader>
          <CardContent>
            {cashFlow.length > 0 ? (
              <CashFlowBar data={cashFlow} />
            ) : (
              <div className="flex items-center justify-center h-64 text-slate-500">
                No cash flow data
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 4: Recent Transactions */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white text-lg">
            Recent Transactions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {recentTx.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="text-left px-4 py-3 text-slate-400 font-medium">
                      Date
                    </th>
                    <th className="text-left px-4 py-3 text-slate-400 font-medium">
                      Institution
                    </th>
                    <th className="text-left px-4 py-3 text-slate-400 font-medium">
                      Description
                    </th>
                    <th className="text-left px-4 py-3 text-slate-400 font-medium">
                      Category
                    </th>
                    <th className="text-right px-4 py-3 text-slate-400 font-medium">
                      Amount
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {recentTx.map((tx: any, i: number) => (
                    <tr
                      key={tx.id || i}
                      className="border-b border-slate-800/50 hover:bg-slate-800/30"
                    >
                      <td className="px-4 py-3 text-slate-300">
                        {formatDate(tx.date)}
                      </td>
                      <td className="px-4 py-3 text-white font-medium">
                        {tx.institution}
                      </td>
                      <td className="px-4 py-3 text-slate-300 max-w-xs truncate">
                        {tx.description}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full capitalize">
                          {tx.category || 'other'}
                        </span>
                      </td>
                      <td
                        className={cn(
                          'px-4 py-3 text-right font-medium',
                          tx.type === 'debit'
                            ? 'text-rose-400'
                            : 'text-emerald-400'
                        )}
                      >
                        {tx.type === 'debit' ? '-' : '+'}
                        {formatIDR(Math.abs(tx.amount))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              No recent transactions
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
