import { useState } from 'react';
import Modal from '../../components/ui/Modal';
import Button from '../../components/ui/Button';

interface RejectOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onReject: (reason: string) => void;
}

export default function RejectOrderModal({
  isOpen,
  onClose,
  onReject,
}: RejectOrderModalProps) {
  const [reason, setReason] = useState('');

  const handleSubmit = () => {
    if (!reason.trim()) {
      alert('Пожалуйста, укажите причину отклонения');
      return;
    }
    onReject(reason);
    setReason('');
  };

  const commonReasons = [
    'Товара нет в наличии',
    'Не можем выполнить в указанные сроки',
    'Минимальная сумма заказа не достигнута',
    'Ошибка в заказе',
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Отклонение заказа">
      <div className="space-y-4">
        <p className="text-gray-600">
          Пожалуйста, укажите причину отклонения заказа. Покупатель увидит это сообщение.
        </p>

        {/* Quick Reasons */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Быстрый выбор:
          </label>
          <div className="flex flex-wrap gap-2">
            {commonReasons.map((commonReason) => (
              <button
                key={commonReason}
                onClick={() => setReason(commonReason)}
                className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                  reason === commonReason
                    ? 'border-primary-600 bg-primary-50 text-primary-700'
                    : 'border-gray-300 hover:border-primary-400 text-gray-700'
                }`}
              >
                {commonReason}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Reason */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Или напишите свою причину:
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Опишите причину отклонения заказа..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            rows={4}
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end pt-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            Отмена
          </Button>
          <Button variant="danger" onClick={handleSubmit}>
            Отклонить заказ
          </Button>
        </div>
      </div>
    </Modal>
  );
}
