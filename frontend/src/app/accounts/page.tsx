'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Landmark,
  CreditCard,
  TrendingUp,
  Wallet,
  Building2,
  User,
} from 'lucide-react';
import { getAccounts, getPersons } from '@/lib/api';
import { formatIDR, cn } from '@/lib/formatters';

const INSTITUTION_ICONS: Record<string, typeof Landmark> = {
  bank: Landmark,
  brokerage: TrendingUp,
  wallet: Wallet,
  card: CreditCard,
};

function maskAccountNumber(num: string): string {
  if (!num || num.length < 4) return num || '****';
  return '****' + num.slice(-4);
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'bg-emerald-500/20 text-emerald-400';
  if (confidence >= 0.5) return 'bg-amber-500/20 text-amber-400';
  return 'bg-rose-500/20 text-rose-400';
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [persons, setPersons] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [accountsData, personsData] = await Promise.allSettled([
          getAccounts(),
          getPersons(),
        ]);
        if (accountsData.status === 'fulfilled')
          setAccounts(
            accountsData.value?.accounts || accountsData.value?.data || accountsData.value || []
          );
        if (personsData.status === 'fulfilled')
          setPersons(
            personsData.value?.persons || personsData.value?.data || personsData.value || []
          );
      } catch (err) {
        console.error('Failed to fetch accounts:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  // Group accounts by person
  const groupedAccounts = persons.length > 0
    ? persons.map((person: any) => ({
        person,
        accounts: accounts.filter(
          (a: any) =>
            a.person_id === person.id ||
            a.person_name === person.name
        ),
      }))
    : [{ person: null, accounts }];

  // Include ungrouped accounts
  const groupedIds = new Set(
    groupedAccounts.flatMap((g) => g.accounts.map((a: any) => a.id))
  );
  const ungrouped = accounts.filter((a: any) => !groupedIds.has(a.id));
  if (ungrouped.length > 0 && persons.length > 0) {
    groupedAccounts.push({ person: null, accounts: ungrouped });
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Accounts</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="bg-slate-900 border-slate-800">
              <CardContent className="p-6">
                <div className="animate-pulse space-y-3">
                  <div className="h-5 bg-slate-800 rounded w-1/2"></div>
                  <div className="h-4 bg-slate-800 rounded w-1/3"></div>
                  <div className="h-8 bg-slate-800 rounded w-2/3"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <Landmark className="h-6 w-6 text-emerald-400" />
        <h1 className="text-2xl font-bold text-white">Accounts</h1>
      </div>

      {accounts.length === 0 ? (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-12 text-center">
            <Building2 className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <p className="text-lg text-slate-400">No accounts found</p>
            <p className="text-sm text-slate-500 mt-1">
              Upload financial documents to detect accounts automatically
            </p>
          </CardContent>
        </Card>
      ) : (
        groupedAccounts.map((group, groupIdx) => (
          <div key={groupIdx} className="space-y-4">
            {group.person && (
              <div className="flex items-center gap-2">
                <User className="h-5 w-5 text-slate-400" />
                <h2 className="text-lg font-semibold text-white">
                  {group.person.name}
                </h2>
              </div>
            )}
            {!group.person && persons.length > 0 && (
              <div className="flex items-center gap-2">
                <User className="h-5 w-5 text-slate-500" />
                <h2 className="text-lg font-semibold text-slate-400">
                  Other Accounts
                </h2>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {group.accounts.map((account: any, idx: number) => {
                const accountType = (
                  account.type ||
                  account.account_type ||
                  'bank'
                ).toLowerCase();
                const Icon =
                  INSTITUTION_ICONS[accountType] || Landmark;

                return (
                  <Card
                    key={account.id || idx}
                    className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors"
                  >
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-slate-800 rounded-lg">
                            <Icon className="h-5 w-5 text-emerald-400" />
                          </div>
                          <div>
                            <p className="font-semibold text-white">
                              {account.institution ||
                                account.bank ||
                                account.name}
                            </p>
                            <p className="text-xs text-slate-500 capitalize">
                              {account.type ||
                                account.account_type ||
                                'Account'}
                            </p>
                          </div>
                        </div>
                        {account.confidence !== undefined && (
                          <Badge
                            variant="secondary"
                            className={cn(
                              'text-xs',
                              getConfidenceColor(account.confidence)
                            )}
                          >
                            {(account.confidence * 100).toFixed(0)}%
                          </Badge>
                        )}
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-500">
                            Account
                          </span>
                          <span className="text-sm text-slate-300 font-mono">
                            {maskAccountNumber(
                              account.account_number ||
                                account.number ||
                                ''
                            )}
                          </span>
                        </div>

                        <div className="pt-2 border-t border-slate-800">
                          <p className="text-xs text-slate-500 mb-1">
                            {accountType === 'brokerage' ||
                            accountType === 'investment'
                              ? 'Portfolio Value'
                              : 'Balance'}
                          </p>
                          <p className="text-lg font-bold text-white">
                            {formatIDR(
                              account.balance ||
                                account.portfolio_value ||
                                account.value ||
                                0
                            )}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
