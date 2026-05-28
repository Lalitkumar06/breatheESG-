
interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

const STATUS_CONFIG: Record<string, { label: string; dot: string }> = {
  PENDING_REVIEW: { label: 'Pending', dot: '#ffab40' },
  APPROVED:       { label: 'Approved', dot: '#00e676' },
  REJECTED:       { label: 'Rejected', dot: '#ff5252' },
  FLAGGED:        { label: 'Flagged', dot: '#b388ff' },
  PENDING:        { label: 'Pending', dot: '#ffab40' },
  PROCESSING:     { label: 'Processing', dot: '#82b1ff' },
  COMPLETE:       { label: 'Complete', dot: '#00e676' },
  FAILED:         { label: 'Failed', dot: '#ff5252' },
};

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status?.toUpperCase()] || { label: status, dot: '#8ba3c7' };
  const cls = `badge badge-${status?.toLowerCase()?.replace('_review', '')}`;

  return (
    <span className={cls} style={size === 'sm' ? { fontSize: 10, padding: '1px 8px' } : {}}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: config.dot, flexShrink: 0,
        boxShadow: `0 0 6px ${config.dot}80`,
      }} />
      {config.label}
    </span>
  );
}
