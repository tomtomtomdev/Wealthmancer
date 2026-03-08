'use client';

import { Upload } from 'lucide-react';
import DropZone from '@/components/upload/DropZone';
import { uploadDocuments } from '@/lib/api';

export default function UploadPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Upload className="h-6 w-6 text-emerald-400" />
          <h1 className="text-2xl font-bold text-white">Upload Documents</h1>
        </div>
        <p className="text-slate-400">
          Upload your bank statements, brokerage reports, and other financial
          documents. We will extract and consolidate your financial data
          automatically.
        </p>
      </div>

      <DropZone onUpload={uploadDocuments} />
    </div>
  );
}
