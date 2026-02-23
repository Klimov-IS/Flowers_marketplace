import Modal from '../../../components/ui/Modal';
import ImportHistory from './ImportHistory';

interface ImportHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  supplierId: string;
}

export default function ImportHistoryModal({ isOpen, onClose, supplierId }: ImportHistoryModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="История загрузок" size="xl">
      <ImportHistory supplierId={supplierId} compact />
    </Modal>
  );
}
