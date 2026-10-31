'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { TriageInbox } from '@/components/triage/TriageInbox';

export default function IssuesInboxPage() {
  const params = useParams();
  const repoId = String(params.id || '');

  return <TriageInbox repoId={repoId} />;
}
