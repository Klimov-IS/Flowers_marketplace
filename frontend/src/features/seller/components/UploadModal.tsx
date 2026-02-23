import Modal from '../../../components/ui/Modal';
import PriceListUpload from '../PriceListUpload';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function UploadModal({ isOpen, onClose }: UploadModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Загрузка прайс-листа" size="lg">
      <PriceListUpload showHistory={false} onUploadSuccess={onClose} />
    </Modal>
  );
}
