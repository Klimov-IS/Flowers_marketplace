import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import { setCredentials } from './authSlice';
import { useLoginMutation } from './authApi';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';

export default function LoginPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [login, { isLoading }] = useLoginMutation();

  const [role, setRole] = useState<'buyer' | 'supplier'>('buyer');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!email || !password) {
      setErrorMessage('Введите email и пароль');
      return;
    }

    try {
      const tokens = await login({ email, password, role }).unwrap();

      // Fetch user info with the new token
      const response = await fetch('/auth/me', {
        headers: {
          Authorization: `Bearer ${tokens.access_token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch user info');
      }

      const user = await response.json();

      // Store credentials
      dispatch(
        setCredentials({
          user: {
            id: user.id,
            name: user.name,
            email: user.email,
            role: user.role === 'supplier' ? 'seller' : 'buyer',
          },
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        })
      );

      // Navigate to dashboard
      navigate(user.role === 'supplier' ? '/seller' : '/buyer');
    } catch (err: any) {
      console.error('Login error:', err);
      if (err.data?.detail) {
        setErrorMessage(err.data.detail);
      } else {
        setErrorMessage('Ошибка входа. Проверьте email и пароль.');
      }
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold text-center mb-6">Вход в систему</h1>

        <form onSubmit={handleLogin} className="space-y-4">
          {/* Role Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Выберите роль
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
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
                type="button"
                onClick={() => setRole('supplier')}
                className={`p-4 border-2 rounded-lg text-center transition-colors ${
                  role === 'supplier'
                    ? 'border-primary-600 bg-primary-50'
                    : 'border-gray-300 hover:border-primary-400'
                }`}
              >
                <div className="font-semibold">Продавец</div>
                <div className="text-xs text-gray-500 mt-1">Поставщик, база</div>
              </button>
            </div>
          </div>

          {/* Email */}
          <Input
            label="Email"
            type="email"
            placeholder="example@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          {/* Password */}
          <Input
            label="Пароль"
            type="password"
            placeholder="Введите пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {/* Error Message */}
          {errorMessage && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {errorMessage}
            </div>
          )}

          {/* Submit Button */}
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Вход...' : `Войти как ${role === 'buyer' ? 'покупатель' : 'продавец'}`}
          </Button>
        </form>

        {/* Register Link */}
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            Нет аккаунта?{' '}
            <a href="/register" className="text-primary-600 hover:underline">
              Зарегистрироваться
            </a>
          </p>
        </div>
      </Card>
    </div>
  );
}
