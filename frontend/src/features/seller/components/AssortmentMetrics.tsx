import Card from '../../../components/ui/Card';
import type { AssortmentMetrics as AssortmentMetricsType } from '../supplierApi';

interface AssortmentMetricsProps {
  metrics?: AssortmentMetricsType;
}

export default function AssortmentMetrics({ metrics }: AssortmentMetricsProps) {
  if (!metrics) return null;

  const cards = [
    { label: 'Всего позиций', value: metrics.total_items, color: 'text-primary-600' },
    { label: 'Опубликовано', value: metrics.published, color: 'text-green-600' },
    { label: 'На проверке', value: metrics.needs_review, color: 'text-orange-600' },
    { label: 'Ошибки', value: metrics.errors, color: 'text-red-600' },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      {cards.map((card) => (
        <Card key={card.label} className="p-6 text-center">
          <div className={`text-4xl font-bold ${card.color} mb-2`}>
            {card.value}
          </div>
          <div className="text-gray-600">{card.label}</div>
        </Card>
      ))}
    </div>
  );
}
