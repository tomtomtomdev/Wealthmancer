'use client';

import { useState, useCallback, useRef } from 'react';
import { Upload, X, FileText, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/formatters';

interface FileItem {
  file: File;
  status: 'pending' | 'uploading' | 'extracting' | 'done' | 'error';
  progress: number;
  result?: any;
  error?: string;
}

interface Props {
  onUpload: (files: File[]) => Promise<any>;
}

export default function DropZone({ onUpload }: Props) {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState<any>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const pdfFiles = Array.from(newFiles).filter(
      (f) => f.type === 'application/pdf' || f.name.endsWith('.pdf')
    );
    setFiles((prev) => [
      ...prev,
      ...pdfFiles.map((file) => ({
        file,
        status: 'pending' as const,
        progress: 0,
      })),
    ]);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (!files.length) return;
    setIsUploading(true);

    // Set all to uploading
    setFiles((prev) =>
      prev.map((f) => ({ ...f, status: 'uploading' as const, progress: 30 }))
    );

    try {
      // Simulate progress stages
      setTimeout(() => {
        setFiles((prev) =>
          prev.map((f) => ({ ...f, status: 'extracting' as const, progress: 60 }))
        );
      }, 1000);

      const result = await onUpload(files.map((f) => f.file));
      setUploadResults(result);

      setFiles((prev) =>
        prev.map((f) => ({
          ...f,
          status: 'done' as const,
          progress: 100,
          result,
        }))
      );
    } catch (err: any) {
      setFiles((prev) =>
        prev.map((f) => ({
          ...f,
          status: 'error' as const,
          progress: 0,
          error: err.message || 'Upload failed',
        }))
      );
    } finally {
      setIsUploading(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const allDone = files.length > 0 && files.every((f) => f.status === 'done');

  return (
    <div className="space-y-6">
      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all',
          isDragOver
            ? 'border-emerald-400 bg-emerald-400/5'
            : 'border-slate-700 hover:border-slate-500 bg-slate-900/50'
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
        <Upload
          className={cn(
            'h-12 w-12 mx-auto mb-4',
            isDragOver ? 'text-emerald-400' : 'text-slate-500'
          )}
        />
        <p className="text-lg font-medium text-slate-300 mb-1">
          Drop PDF files here or click to browse
        </p>
        <p className="text-sm text-slate-500">
          Supports bank statements, brokerage reports, and financial documents
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-slate-400">
            Selected Files ({files.length})
          </h3>
          {files.map((item, index) => (
            <div
              key={index}
              className="flex items-center gap-3 bg-slate-900 border border-slate-800 rounded-lg px-4 py-3"
            >
              <FileText className="h-5 w-5 text-slate-500 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">
                  {item.file.name}
                </p>
                <p className="text-xs text-slate-500">
                  {formatSize(item.file.size)}
                </p>
                {(item.status === 'uploading' ||
                  item.status === 'extracting') && (
                  <div className="mt-2">
                    <Progress
                      value={item.progress}
                      className="h-1.5 bg-slate-800"
                    />
                    <p className="text-xs text-slate-400 mt-1 capitalize">
                      {item.status}...
                    </p>
                  </div>
                )}
                {item.status === 'error' && (
                  <p className="text-xs text-rose-400 mt-1">{item.error}</p>
                )}
              </div>
              <div className="flex-shrink-0">
                {item.status === 'pending' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(index);
                    }}
                    className="p-1 hover:bg-slate-800 rounded"
                  >
                    <X className="h-4 w-4 text-slate-500" />
                  </button>
                )}
                {(item.status === 'uploading' ||
                  item.status === 'extracting') && (
                  <Loader2 className="h-5 w-5 text-emerald-400 animate-spin" />
                )}
                {item.status === 'done' && (
                  <CheckCircle className="h-5 w-5 text-emerald-400" />
                )}
                {item.status === 'error' && (
                  <AlertCircle className="h-5 w-5 text-rose-400" />
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload button */}
      {files.length > 0 && !allDone && (
        <Button
          onClick={handleUpload}
          disabled={isUploading || files.every((f) => f.status !== 'pending')}
          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
          size="lg"
        >
          {isUploading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4 mr-2" />
              Upload {files.length} file{files.length > 1 ? 's' : ''}
            </>
          )}
        </Button>
      )}

      {/* Results summary */}
      {allDone && uploadResults && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-emerald-400" />
            <h3 className="text-lg font-medium text-white">
              Upload Complete
            </h3>
          </div>
          {uploadResults.documents?.map((doc: any, i: number) => (
            <div
              key={i}
              className="bg-slate-800/50 rounded-lg p-4 space-y-2"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-white">
                  {doc.filename || doc.file_name || `Document ${i + 1}`}
                </p>
                {doc.confidence && (
                  <span
                    className={cn(
                      'text-xs font-medium px-2 py-0.5 rounded-full',
                      doc.confidence > 0.8
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : doc.confidence > 0.5
                        ? 'bg-amber-500/20 text-amber-400'
                        : 'bg-rose-500/20 text-rose-400'
                    )}
                  >
                    {(doc.confidence * 100).toFixed(0)}% confidence
                  </span>
                )}
              </div>
              {doc.institution && (
                <p className="text-sm text-slate-400">
                  Institution: <span className="text-slate-300">{doc.institution}</span>
                </p>
              )}
              {doc.document_type && (
                <p className="text-sm text-slate-400">
                  Type: <span className="text-slate-300">{doc.document_type}</span>
                </p>
              )}
              {doc.extracted_data && (
                <p className="text-sm text-slate-400">
                  Extracted:{' '}
                  <span className="text-slate-300">
                    {Object.keys(doc.extracted_data).length} data fields
                  </span>
                </p>
              )}
            </div>
          ))}
          <a href="/dashboard">
            <Button className="w-full bg-emerald-600 hover:bg-emerald-700 text-white mt-4">
              View Dashboard
            </Button>
          </a>
        </div>
      )}
    </div>
  );
}
