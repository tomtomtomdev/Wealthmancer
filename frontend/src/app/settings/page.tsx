'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Settings as SettingsIcon,
  Mail,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  XCircle,
  Search,
  Download,
  Paperclip,
  HelpCircle,
} from 'lucide-react';
import { cn } from '@/lib/formatters';
import {
  getSettings,
  saveSettings,
  testGmailConnection,
  searchGmail,
  importFromGmail,
} from '@/lib/api';

const DEFAULT_KEYWORDS =
  'statement, billing, tagihan, rekening, sekuritas, portfolio, soa, e-statement, mutasi';

interface EmailResult {
  subject: string;
  date: string;
  sender: string;
  message_id: string;
  attachments: {
    filename: string;
    size: number;
    path?: string;
  }[];
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function SettingsPage() {
  // Gmail settings state
  const [email, setEmail] = useState('');
  const [appPassword, setAppPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [keywords, setKeywords] = useState(DEFAULT_KEYWORDS);

  // Connection test state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Save state
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<{ success: boolean; message: string } | null>(null);

  // Search state
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<EmailResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Selection state
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());

  // Import state
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [importResult, setImportResult] = useState<{
    success: boolean;
    documents_created?: number;
    duplicates_skipped?: number;
    message?: string;
  } | null>(null);

  // Loading state
  const [loadingSettings, setLoadingSettings] = useState(true);

  // Load existing settings on mount
  useEffect(() => {
    async function loadSettings() {
      try {
        const data = await getSettings();
        const settings = data?.settings || data || {};
        if (settings.gmail_email) setEmail(settings.gmail_email);
        if (settings.gmail_password) setAppPassword(settings.gmail_password);
        if (settings.gmail_keywords) setKeywords(settings.gmail_keywords);
      } catch (err) {
        console.error('Failed to load settings:', err);
      } finally {
        setLoadingSettings(false);
      }
    }
    loadSettings();
  }, []);

  const handleTestConnection = useCallback(async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testGmailConnection(email, appPassword);
      setTestResult({
        success: result.success ?? result.status === 'ok',
        message: result.message || (result.success ? 'Connection successful!' : 'Connection failed.'),
      });
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || 'Connection test failed.',
      });
    } finally {
      setTesting(false);
    }
  }, [email, appPassword]);

  const handleSaveSettings = useCallback(async () => {
    setSaving(true);
    setSaveResult(null);
    try {
      const result = await saveSettings({
        gmail_email: email,
        gmail_password: appPassword,
        gmail_keywords: keywords,
      });
      setSaveResult({
        success: result.success ?? true,
        message: result.message || 'Settings saved successfully!',
      });
    } catch (err: any) {
      setSaveResult({
        success: false,
        message: err.message || 'Failed to save settings.',
      });
    } finally {
      setSaving(false);
    }
  }, [email, appPassword, keywords]);

  const handleSearch = useCallback(async () => {
    setSearching(true);
    setSearchError(null);
    setSearchResults([]);
    setSelectedPaths(new Set());
    setImportResult(null);
    try {
      const keywordList = keywords
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean);
      const result = await searchGmail({
        email,
        password: appPassword,
        keywords: keywordList,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      if (result.error) {
        setSearchError(result.error);
      } else {
        setSearchResults(result.results || result.emails || []);
      }
    } catch (err: any) {
      setSearchError(err.message || 'Search failed.');
    } finally {
      setSearching(false);
    }
  }, [email, appPassword, keywords, dateFrom, dateTo]);

  const allAttachmentPaths = searchResults.flatMap((r) =>
    r.attachments.map((a) => a.path || `${r.message_id}/${a.filename}`)
  );

  const handleSelectAll = () => {
    setSelectedPaths(new Set(allAttachmentPaths));
  };

  const handleDeselectAll = () => {
    setSelectedPaths(new Set());
  };

  const toggleSelection = (path: string) => {
    setSelectedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const handleImport = useCallback(async () => {
    const paths = Array.from(selectedPaths);
    if (paths.length === 0) return;
    setImporting(true);
    setImportProgress(0);
    setImportResult(null);

    // Simulate progress increments
    const progressInterval = setInterval(() => {
      setImportProgress((prev) => {
        if (prev >= 90) return prev;
        return prev + Math.random() * 15;
      });
    }, 500);

    try {
      const result = await importFromGmail(paths);
      setImportProgress(100);
      setImportResult({
        success: result.success ?? !result.error,
        documents_created: result.documents_created ?? result.imported ?? 0,
        duplicates_skipped: result.duplicates_skipped ?? result.skipped ?? 0,
        message: result.message || result.error,
      });
    } catch (err: any) {
      setImportResult({
        success: false,
        message: err.message || 'Import failed.',
      });
    } finally {
      clearInterval(progressInterval);
      setImporting(false);
    }
  }, [selectedPaths]);

  if (loadingSettings) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <SettingsIcon className="h-6 w-6 text-emerald-400" />
          <h1 className="text-2xl font-bold text-white">Settings</h1>
        </div>
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-5 bg-slate-800 rounded w-1/3"></div>
              <div className="h-8 bg-slate-800 rounded w-full"></div>
              <div className="h-8 bg-slate-800 rounded w-full"></div>
              <div className="h-8 bg-slate-800 rounded w-2/3"></div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-4xl">
      <div className="flex items-center gap-3">
        <SettingsIcon className="h-6 w-6 text-emerald-400" />
        <h1 className="text-2xl font-bold text-white">Settings</h1>
      </div>

      {/* Section 1: Gmail Integration */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <Mail className="h-5 w-5 text-emerald-400" />
            Gmail Integration
          </CardTitle>
          <CardDescription className="text-slate-400">
            Connect your Gmail account to automatically import financial statements and documents.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Email */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Email Address</label>
            <Input
              type="email"
              placeholder="your.email@gmail.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500"
            />
          </div>

          {/* App Password */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">App Password</label>
            <div className="relative">
              <Input
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter your Gmail App Password"
                value={appPassword}
                onChange={(e) => setAppPassword(e.target.value)}
                className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-300 transition-colors"
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            <div className="flex items-start gap-2 mt-1">
              <HelpCircle className="h-4 w-4 text-slate-500 mt-0.5 shrink-0" />
              <p className="text-xs text-slate-500">
                Use a Gmail App Password. Go to Google Account &gt; Security &gt; 2-Step
                Verification &gt; App Passwords to create one.
              </p>
            </div>
          </div>

          {/* Search Keywords */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Search Keywords</label>
            <Input
              type="text"
              placeholder="statement, billing, tagihan, ..."
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500"
            />
            <p className="text-xs text-slate-500">Comma-separated keywords to filter emails.</p>
          </div>

          {/* Test & Save buttons */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              onClick={handleTestConnection}
              disabled={testing || !email || !appPassword}
              variant="outline"
              className="border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800"
            >
              {testing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                  Testing...
                </>
              ) : (
                'Test Connection'
              )}
            </Button>

            <Button
              onClick={handleSaveSettings}
              disabled={saving}
              className="bg-emerald-600 text-white hover:bg-emerald-500"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                  Saving...
                </>
              ) : (
                'Save Settings'
              )}
            </Button>
          </div>

          {/* Test result */}
          {testResult && (
            <div
              className={cn(
                'flex items-center gap-2 rounded-lg px-3 py-2 text-sm',
                testResult.success
                  ? 'bg-emerald-500/10 text-emerald-400'
                  : 'bg-rose-500/10 text-rose-400'
              )}
            >
              {testResult.success ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 shrink-0" />
              )}
              {testResult.message}
            </div>
          )}

          {/* Save result */}
          {saveResult && (
            <div
              className={cn(
                'flex items-center gap-2 rounded-lg px-3 py-2 text-sm',
                saveResult.success
                  ? 'bg-emerald-500/10 text-emerald-400'
                  : 'bg-rose-500/10 text-rose-400'
              )}
            >
              {saveResult.success ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 shrink-0" />
              )}
              {saveResult.message}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 2: Search & Import from Gmail */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <Search className="h-5 w-5 text-emerald-400" />
            Search &amp; Import from Gmail
          </CardTitle>
          <CardDescription className="text-slate-400">
            Search your Gmail for financial documents and import them into Wealthmancer.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Date range */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">From Date</label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="bg-slate-800/50 border-slate-700 text-white"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">To Date</label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="bg-slate-800/50 border-slate-700 text-white"
              />
            </div>
          </div>

          {/* Search button */}
          <Button
            onClick={handleSearch}
            disabled={searching || !email || !appPassword}
            className="bg-emerald-600 text-white hover:bg-emerald-500"
          >
            {searching ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                Searching...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-1.5" />
                Search Gmail
              </>
            )}
          </Button>

          {/* Search error */}
          {searchError && (
            <div className="flex items-center gap-2 rounded-lg bg-rose-500/10 px-3 py-2 text-sm text-rose-400">
              <XCircle className="h-4 w-4 shrink-0" />
              {searchError}
            </div>
          )}

          {/* Search results */}
          {searchResults.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-400">
                  Found {searchResults.length} email{searchResults.length !== 1 ? 's' : ''} with{' '}
                  {allAttachmentPaths.length} attachment
                  {allAttachmentPaths.length !== 1 ? 's' : ''}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSelectAll}
                    className="border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800"
                  >
                    Select All
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDeselectAll}
                    className="border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800"
                  >
                    Deselect All
                  </Button>
                </div>
              </div>

              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {searchResults.map((result, idx) => (
                  <div
                    key={result.message_id || idx}
                    className="rounded-lg border border-slate-800 bg-slate-800/30 p-4 space-y-3"
                  >
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-white">{result.subject}</p>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <span>{result.sender}</span>
                        <span className="text-slate-700">|</span>
                        <span>{result.date}</span>
                      </div>
                    </div>

                    {result.attachments.length > 0 && (
                      <div className="space-y-1.5">
                        {result.attachments.map((att, attIdx) => {
                          const path =
                            att.path || `${result.message_id}/${att.filename}`;
                          const isSelected = selectedPaths.has(path);
                          return (
                            <label
                              key={attIdx}
                              className={cn(
                                'flex items-center gap-3 rounded-md px-3 py-2 cursor-pointer transition-colors',
                                isSelected
                                  ? 'bg-emerald-500/10 border border-emerald-500/30'
                                  : 'bg-slate-800/50 border border-slate-700/50 hover:bg-slate-800'
                              )}
                            >
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleSelection(path)}
                                className="rounded border-slate-600 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0 bg-slate-800"
                              />
                              <Paperclip className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                              <span className="text-sm text-slate-300 truncate flex-1">
                                {att.filename}
                              </span>
                              <Badge
                                variant="secondary"
                                className="bg-slate-700/50 text-slate-400 text-xs"
                              >
                                {formatFileSize(att.size)}
                              </Badge>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Import button */}
              <div className="flex items-center gap-3 pt-2">
                <Button
                  onClick={handleImport}
                  disabled={importing || selectedPaths.size === 0}
                  className="bg-emerald-600 text-white hover:bg-emerald-500"
                >
                  {importing ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                      Importing {selectedPaths.size} file{selectedPaths.size !== 1 ? 's' : ''}...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4 mr-1.5" />
                      Import Selected ({selectedPaths.size})
                    </>
                  )}
                </Button>
              </div>

              {/* Import progress */}
              {importing && (
                <div className="space-y-2">
                  <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 transition-all duration-300 rounded-full"
                      style={{ width: `${Math.min(importProgress, 100)}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 text-center">
                    {Math.round(importProgress)}% complete
                  </p>
                </div>
              )}

              {/* Import result */}
              {importResult && (
                <div
                  className={cn(
                    'rounded-lg px-4 py-3 text-sm space-y-1',
                    importResult.success
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-rose-500/10 text-rose-400'
                  )}
                >
                  <div className="flex items-center gap-2">
                    {importResult.success ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 shrink-0" />
                    )}
                    <span className="font-medium">
                      {importResult.success ? 'Import complete!' : 'Import failed'}
                    </span>
                  </div>
                  {importResult.success && (
                    <div className="pl-6 space-y-0.5 text-slate-400">
                      <p>Documents created: {importResult.documents_created ?? 0}</p>
                      <p>Duplicates skipped: {importResult.duplicates_skipped ?? 0}</p>
                    </div>
                  )}
                  {importResult.message && !importResult.success && (
                    <p className="pl-6">{importResult.message}</p>
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
