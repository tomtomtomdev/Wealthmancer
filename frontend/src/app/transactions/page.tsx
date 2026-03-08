'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ArrowLeftRight, Search } from 'lucide-react';
import { getTransactions } from '@/lib/api';
import TransactionsTable from '@/components/tables/TransactionsTable';

export default function TransactionsPage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({
    search: '',
    institution: '',
    type: '',
    category: '',
    date_from: '',
    date_to: '',
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getTransactions({
        page,
        limit: 20,
        ...filters,
      });
      setData(result?.transactions || result?.data || result || []);
      setTotalPages(result?.total_pages || result?.pages || 1);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const updateFilter = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ArrowLeftRight className="h-6 w-6 text-emerald-400" />
        <h1 className="text-2xl font-bold text-white">Transactions</h1>
      </div>

      {/* Filter Bar */}
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <Input
                placeholder="Search..."
                value={filters.search}
                onChange={(e) => updateFilter('search', e.target.value)}
                className="pl-9 bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
              />
            </div>

            <Input
              type="date"
              placeholder="From"
              value={filters.date_from}
              onChange={(e) => updateFilter('date_from', e.target.value)}
              className="bg-slate-800 border-slate-700 text-white"
            />

            <Input
              type="date"
              placeholder="To"
              value={filters.date_to}
              onChange={(e) => updateFilter('date_to', e.target.value)}
              className="bg-slate-800 border-slate-700 text-white"
            />

            <select
              value={filters.institution}
              onChange={(e) => updateFilter('institution', e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Institutions</option>
              <option value="BCA">BCA</option>
              <option value="Mandiri">Mandiri</option>
              <option value="BNI">BNI</option>
              <option value="BRI">BRI</option>
              <option value="Stockbit">Stockbit</option>
              <option value="Bibit">Bibit</option>
            </select>

            <select
              value={filters.type}
              onChange={(e) => updateFilter('type', e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Types</option>
              <option value="debit">Debit</option>
              <option value="credit">Credit</option>
            </select>

            <select
              value={filters.category}
              onChange={(e) => updateFilter('category', e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Categories</option>
              <option value="transfer">Transfer</option>
              <option value="salary">Salary</option>
              <option value="food">Food</option>
              <option value="shopping">Shopping</option>
              <option value="utilities">Utilities</option>
              <option value="investment">Investment</option>
              <option value="entertainment">Entertainment</option>
              <option value="transport">Transport</option>
              <option value="healthcare">Healthcare</option>
              <option value="other">Other</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Transactions Table */}
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-6">
          {loading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-4 bg-slate-800 rounded w-1/4"></div>
              {[...Array(10)].map((_, i) => (
                <div key={i} className="h-10 bg-slate-800/50 rounded"></div>
              ))}
            </div>
          ) : (
            <TransactionsTable
              data={data}
              page={page}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
