import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import { setUser } from './authSlice';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';

export default function LoginPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [role, setRole] = useState<'buyer' | 'seller'>('buyer');

  const handleLogin = () => {
    // MVP: Mock login
    const mockUser = {
      id: role === 'buyer' ? 'buyer-1' : 'supplier-1',
      name: role === 'buyer' ? 'Магазин цветов №1' : 'База №1',
      email: `${role}@example.com`,
      role: role as 'buyer' | 'seller',
    };

    dispatch(setUser(mockUser));
    navigate(role === 'buyer' ? '/buyer' : '/seller');
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold text-center mb-6">Вход в систему</h1>
        <p className="text-center text-gray-600 mb-6 text-sm">
          MVP: Выберите роль для входа (без пароля)
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Выберите роль
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setRole('buyer')}
                className={`p-4 border-2 rounded-lg text-center transition-colors ${
                  role === 'buyer'
                    ? 'border-primary-600 bg-primary-50'
                    : 'border-gray-300 hover:border-primary-400'
                }`}
              >
                <div className="font-semibold">Покупатель</div>
                <div className="text-xs text-gray-500 mt-1">Флорист, магазин</div>
              </button>
              <button
                onClick={() => setRole('seller')}
                className={`p-4 border-2 rounded-lg text-center transition-colors ${
                  role === 'seller'
                    ? 'border-primary-600 bg-primary-50'
                    : 'border-gray-300 hover:border-primary-400'
                }`}
              >
                <div className="font-semibold">Продавец</div>
                <div className="text-xs text-gray-500 mt-1">Поставщик, база</div>
              </button>
            </div>
          </div>

          <Button onClick={handleLogin} className="w-full">
            Войти как {role === 'buyer' ? 'покупатель' : 'продавец'}
          </Button>
        </div>

        <p className="mt-6 text-center text-xs text-gray-500">
          Это MVP версия. Полная аутентификация будет добавлена в Task 4.
        </p>
      </Card>
    </div>
  );
}
