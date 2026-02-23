import { useState, useCallback } from 'react';
import { useAppSelector } from '../../hooks/useAppSelector';
import { useUploadPriceListMutation } from './supplierApi';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import { useToast } from '../../components/ui/Toast';
import ImportHistory from './components/ImportHistory';

interface PriceListUploadProps {
  showHistory?: boolean;
  onUploadSuccess?: () => void;
}

export default function PriceListUpload({ showHistory = true, onUploadSuccess }: PriceListUploadProps) {
  const user = useAppSelector((state) => state.auth.user);
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const { showToast } = useToast();

  const [uploadPriceList, { isLoading }] = useUploadPriceListMutation();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile && isValidFile(droppedFile)) {
        setFile(droppedFile);
      } else {
        showToast('Пожалуйста, загрузите файл в формате CSV, XLSX, PDF или TXT', 'warning');
      }
    },
    [showToast]
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && isValidFile(selectedFile)) {
      setFile(selectedFile);
    } else {
      showToast('Пожалуйста, загрузите файл в формате CSV, XLSX, PDF или TXT', 'warning');
    }
  };

  const isValidFile = (file: File) => {
    const validExtensions = ['.csv', '.xlsx', '.xls', '.txt', '.pdf'];
    return validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));
  };

  const handleUpload = async () => {
    if (!file || !user) return;

    try {
      await uploadPriceList({
        supplier_id: user.id,
        file,
        description,
      }).unwrap();

      showToast('Прайс-лист загружен и обрабатывается', 'success');

      // Reset form
      setFile(null);
      setDescription('');
      onUploadSuccess?.();
    } catch (error) {
      console.error('Upload failed:', error);
      showToast('Ошибка при загрузке прайс-листа', 'error');
    }
  };

  if (!user) {
    return (
      <Card className="p-6">
        <p className="text-gray-600">Пожалуйста, войдите в систему для загрузки прайс-листа.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Загрузка прайс-листа</h3>
        <p className="text-gray-600 mb-4">
          Загрузите файл с прайс-листом (CSV, XLSX, PDF, TXT). Система автоматически обработает и
          нормализует товары.
        </p>

        {/* Drag and Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            isDragging ? 'border-primary-600 bg-primary-50' : 'border-gray-300 bg-gray-50'
          }`}
        >
          <svg
            className="mx-auto h-10 w-10 text-gray-400 mb-3"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          {file ? (
            <div>
              <p className="text-base font-medium text-gray-900 mb-1">
                Выбран файл: {file.name}
              </p>
              <p className="text-sm text-gray-500">Размер: {(file.size / 1024).toFixed(2)} KB</p>
            </div>
          ) : (
            <div>
              <p className="text-base font-medium text-gray-900 mb-1">
                Перетащите файл сюда или выберите файл
              </p>
              <p className="text-sm text-gray-500 mb-3">Поддерживаются форматы: CSV, XLSX, PDF, TXT</p>
              <label className="inline-block">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls,.txt,.pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <span className="cursor-pointer bg-white px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium text-gray-700">
                  Выбрать файл
                </span>
              </label>
            </div>
          )}
        </div>

        {/* Description Input */}
        {file && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Описание (необязательно)
            </label>
            <input
              type="text"
              placeholder="Например: Обновление прайса на февраль 2026"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
        )}

        {/* Upload Button */}
        {file && (
          <div className="mt-4 flex gap-3">
            <Button onClick={handleUpload} disabled={isLoading}>
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Загрузка...
                </span>
              ) : (
                'Загрузить прайс-лист'
              )}
            </Button>
            <Button variant="secondary" onClick={() => setFile(null)} disabled={isLoading}>
              Отмена
            </Button>
          </div>
        )}
      </Card>

      {/* Import History Section */}
      {showHistory && <ImportHistory supplierId={user.id} />}
    </div>
  );
}
