interface AIIndicatorProps {
  source?: 'ai' | 'manual' | 'parser';
  confidence?: number;
  className?: string;
}

/**
 * Indicator showing AI-generated field with confidence level.
 */
export default function AIIndicator({ source, confidence, className = '' }: AIIndicatorProps) {
  if (source !== 'ai') return null;

  const confidencePercent = confidence !== undefined ? Math.round(confidence * 100) : null;

  const getConfidenceColor = () => {
    if (confidence === undefined) return 'text-blue-500';
    if (confidence >= 0.9) return 'text-green-500';
    if (confidence >= 0.7) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getTooltip = () => {
    if (confidencePercent === null) return 'Заполнено AI';
    return `AI (${confidencePercent}%)`;
  };

  return (
    <span
      className={`inline-flex items-center ${getConfidenceColor()} ${className}`}
      title={getTooltip()}
    >
      <svg
        className="w-3.5 h-3.5"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm0 14.5a6.5 6.5 0 110-13 6.5 6.5 0 010 13z" />
        <path d="M10 5.5a1 1 0 011 1v3.5a1 1 0 01-2 0V6.5a1 1 0 011-1zm0 7a1 1 0 100 2 1 1 0 000-2z" />
      </svg>
    </span>
  );
}

/**
 * AI sparkles icon - indicates AI-enhanced content
 */
export function AISparkles({ className = '' }: { className?: string }) {
  return (
    <svg
      className={`w-3.5 h-3.5 text-purple-500 ${className}`}
      fill="currentColor"
      viewBox="0 0 20 20"
      title="Заполнено AI"
    >
      <path
        fillRule="evenodd"
        d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 4.346a1 1 0 01-.593 1.284l-4 1.5a1 1 0 01-.708-1.87l2.893-1.085-1.316-3.29-3.228 1.291v6.913a1 1 0 11-2 0V9.687l-3.228-1.29-1.316 3.29 2.893 1.085a1 1 0 01-.708 1.87l-4-1.5a1 1 0 01-.593-1.284l1.738-4.346-1.233-.617a1 1 0 01.894-1.79l1.599.8L9 4.323V3a1 1 0 011-1z"
        clipRule="evenodd"
      />
    </svg>
  );
}
