import { useState, useCallback } from 'react';
import { useAppSelector } from '../../hooks/useAppSelector';
import { useUploadPriceListMutation } from './supplierApi';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';

export default function PriceListUpload() {
  const user = useAppSelector((state) => state.auth.user);
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  const [uploadPriceList, { isLoading, isSuccess, data: uploadResult }] =
    useUploadPriceListMutation();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && isValidFile(droppedFile)) {
      setFile(droppedFile);
    } else {
      alert('Пожалуйста, загрузите файл в формате CSV, XLSX или TXT');
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && isValidFile(selectedFile)) {
      setFile(selectedFile);
    } else {
      alert('Пожалуйста, загрузите файл в формате CSV, XLSX или TXT');
    }
  };

  const isValidFile = (file: File) => {
    const validExtensions = ['.csv', '.xlsx', '.xls', '.txt'];
    return validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));
  };

  const handleUpload = async () => {
    if (!file || !user) return;

    try {
      const result = await uploadPriceList({
        supplier_id: user.id,
        file,
        description,
      }).unwrap();

      alert(
        `Прайс-лист загружен успешно!\n\n` +
          `Обработано строк: ${result.total_rows}\n` +
          `Успешно: ${result.success_rows}\n` +
          `Ошибок: ${result.error_rows}`
      );

      // Reset form
      setFile(null);
      setDescription('');
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Ошибка при загрузке прайс-листа. Проверьте подключение к API.');
    }
  };

  return (
    <Card className="p-6">
      <p className="text-gray-600 mb-4">
        Загрузите файл с прайс-листом (CSV, XLSX, TXT). Система автоматически обработает и
        нормализует товары.
      </p>

      {/* Drag and Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
          isDragging
            ? 'border-primary-600 bg-primary-50'
            : 'border-gray-300 bg-gray-50'
        }`}
      >
        <svg
          className="mx-auto h-12 w-12 text-gray-400 mb-4"
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
            <p className="text-lg font-medium text-gray-900 mb-2">
              Выбран файл: {file.name}
            </p>
            <p className="text-sm text-gray-500">
              Размер: {(file.size / 1024).toFixed(2)} KB
            </p>
          </div>
        ) : (
          <div>
            <p className="text-lg font-medium text-gray-900 mb-2">
              Перетащите файл сюда или выберите файл
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Поддерживаются форматы: CSV, XLSX, TXT
            </p>
            <label className="inline-block">
              <input
                type="file"
                accept=".csv,.xlsx,.xls,.txt"
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
            placeholder="Например: Обновление прайса на январь 2025"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          />
        </div>
      )}

      {/* Upload Button */}
      {file && (
        <div className="mt-4 flex gap-3">
          <Button onClick={handleUpload} disabled={isLoading || !user}>
            {isLoading ? 'Загрузка...' : 'Загрузить прайс-лист'}
          </Button>
          <Button variant="secondary" onClick={() => setFile(null)}>
            Отмена
          </Button>
        </div>
      )}

      {/* Upload Result */}
      {isSuccess && uploadResult && (
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm font-medium text-green-800 mb-2">
            ✓ Прайс-лист успешно загружен!
          </p>
          <div className="text-sm text-green-700">
            <p>Обработано строк: {uploadResult.total_rows}</p>
            <p>Успешно: {uploadResult.success_rows}</p>
            <p>Ошибок: {uploadResult.error_rows}</p>
          </div>
        </div>
      )}
    </Card>
  );
}
