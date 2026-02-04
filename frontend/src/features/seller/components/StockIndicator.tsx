interface StockIndicatorProps {
  stock: number;
}

type StockLevel = 'high' | 'medium' | 'low' | 'none';

function getStockLevel(stock: number): StockLevel {
  if (stock >= 50) return 'high';
  if (stock >= 20) return 'medium';
  if (stock > 0) return 'low';
  return 'none';
}

const levelStyles: Record<StockLevel, { dot: string; text: string }> = {
  high: {
    dot: 'bg-green-500',
    text: 'text-green-700',
  },
  medium: {
    dot: 'bg-yellow-500',
    text: 'text-yellow-700',
  },
  low: {
    dot: 'bg-red-500',
    text: 'text-red-700',
  },
  none: {
    dot: 'bg-gray-400',
    text: 'text-gray-500',
  },
};

export default function StockIndicator({ stock }: StockIndicatorProps) {
  const level = getStockLevel(stock);
  const styles = levelStyles[level];

  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${styles.dot}`} />
      <span className={`font-medium ${styles.text}`}>
        {stock > 0 ? stock : 'Нет'}
      </span>
    </div>
  );
}
