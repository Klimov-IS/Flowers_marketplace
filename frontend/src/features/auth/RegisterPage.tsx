import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import { setCredentials } from './authSlice';
import { useRegisterBuyerMutation, useRegisterSupplierMutation } from './authApi';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export default function RegisterPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [registerBuyer, { isLoading: isLoadingBuyer }] = useRegisterBuyerMutation();
  const [registerSupplier, { isLoading: isLoadingSupplier }] = useRegisterSupplierMutation();

  const [role, setRole] = useState<'buyer' | 'supplier'>('buyer');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [address, setAddress] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const isLoading = isLoadingBuyer || isLoadingSupplier;

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    // Validation
    if (!name || !email || !phone || !password) {
      setErrorMessage('Заполните все обязательные поля');
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage('Пароли не совпадают');
      return;
    }

    if (password.length < 6) {
      setErrorMessage('Пароль должен содержать минимум 6 символов');
      return;
    }

    try {
      let tokens;

      if (role === 'buyer') {
        tokens = await registerBuyer({
          name,
          email,
          phone,
          password,
          address: address || undefined,
          city_id: '00000000-0000-0000-0000-000000000001', // Default city
        }).unwrap();
      } else {
        tokens = await registerSupplier({
          name,
          email,
          phone,
          password,
          city_id: '00000000-0000-0000-0000-000000000001', // Default city
        }).unwrap();
      }

      // Fetch user info with the new token
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
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
      console.error('Registration error:', err);
      if (err.data?.detail) {
        if (typeof err.data.detail === 'string') {
          setErrorMessage(err.data.detail);
        } else if (Array.isArray(err.data.detail)) {
          setErrorMessage(err.data.detail.map((d: any) => d.msg).join(', '));
        }
      } else {
        setErrorMessage('Ошибка регистрации. Попробуйте позже.');
      }
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-8">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold text-center mb-6">Регистрация</h1>

        <form onSubmit={handleRegister} className="space-y-4">
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

          {/* Name */}
          <Input
            label={role === 'buyer' ? 'Имя / Название магазина' : 'Название компании'}
            type="text"
            placeholder={role === 'buyer' ? 'Иван Иванов' : 'ООО Цветы оптом'}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          {/* Email */}
          <Input
            label="Email"
            type="email"
            placeholder="example@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          {/* Phone */}
          <Input
            label="Телефон"
            type="tel"
            placeholder="+7 (999) 123-45-67"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
          />

          {/* Address (only for buyers) */}
          {role === 'buyer' && (
            <Input
              label="Адрес доставки"
              type="text"
              placeholder="г. Москва, ул. Цветочная, д. 1"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
          )}

          {/* Password */}
          <Input
            label="Пароль"
            type="password"
            placeholder="Минимум 6 символов"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {/* Confirm Password */}
          <Input
            label="Подтверждение пароля"
            type="password"
            placeholder="Повторите пароль"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
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
            {isLoading ? 'Регистрация...' : `Зарегистрироваться как ${role === 'buyer' ? 'покупатель' : 'продавец'}`}
          </Button>
        </form>

        {/* Login Link */}
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            Уже есть аккаунт?{' '}
            <Link to="/login" className="text-primary-600 hover:underline">
              Войти
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
}
