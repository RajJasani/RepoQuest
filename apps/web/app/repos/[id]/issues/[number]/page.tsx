'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { TriageInbox } from '@/components/triage/TriageInbox';

export default function IssueDetailPage() {
  const params = useParams();
  const repoId = String(params.id || '');
  const issueNumber = parseInt(String(params.number || '0'), 10) || undefined;

  return <TriageInbox repoId={repoId} initialIssueNumber={issueNumber} />;
}
