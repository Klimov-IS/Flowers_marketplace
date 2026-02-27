import { useState, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import { setCredentials } from './authSlice';
import { useRegisterBuyerMutation, useRegisterSupplierMutation } from './authApi';
import Input from '../../components/ui/Input';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/* ───── inline SVG icons ───── */
const PersonIcon = (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
  </svg>
);

const EnvelopeIcon = (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
  </svg>
);

const PhoneIcon = (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
  </svg>
);

/* ───── password strength logic ───── */
function getPasswordStrength(pwd: string): { level: number; text: string } {
  if (!pwd) return { level: 0, text: '' };
  if (pwd.length < 6) return { level: 1, text: 'Слабый пароль' };

  const hasNumbers = /\d/.test(pwd);
  const hasSpecial = /[^a-zA-Zа-яА-Я0-9]/.test(pwd);

  if (pwd.length >= 8 && hasNumbers && hasSpecial) return { level: 4, text: 'Надёжный пароль' };
  if (pwd.length >= 8 && hasNumbers) return { level: 3, text: 'Хороший пароль' };
  return { level: 2, text: 'Средний пароль. Добавьте спецсимволы.' };
}

const strengthColors = ['bg-gray-200', 'bg-red-400', 'bg-amber-400', 'bg-lime-500', 'bg-green-500'];

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
  const [showPassword, setShowPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [shaking, setShaking] = useState(false);

  const isLoading = isLoadingBuyer || isLoadingSupplier;
  const strength = useMemo(() => getPasswordStrength(password), [password]);

  const showError = (msg: string) => {
    setErrorMessage(msg);
    setShaking(true);
    setTimeout(() => setShaking(false), 400);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!name || !email || !phone || !password) {
      showError('Заполните все обязательные поля');
      return;
    }
    if (password.length < 6) {
      showError('Пароль должен содержать минимум 6 символов');
      return;
    }
    if (!agreedToTerms) {
      showError('Необходимо принять условия использования');
      return;
    }

    try {
      let tokens;

      if (role === 'buyer') {
        tokens = await registerBuyer({
          name, email, phone, password,
          city_id: '00000000-0000-0000-0000-000000000001',
        }).unwrap();
      } else {
        tokens = await registerSupplier({
          name, email, phone, password,
          city_id: '00000000-0000-0000-0000-000000000001',
        }).unwrap();
      }

      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });

      if (!response.ok) throw new Error('Failed to fetch user info');
      const user = await response.json();

      dispatch(
        setCredentials({
          user: {
            id: user.id,
            name: user.name,
            email: user.email,
            phone: user.phone || undefined,
            role: user.role === 'supplier' ? 'seller' : 'buyer',
            city_name: user.city_name || undefined,
          },
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        })
      );

      navigate(user.role === 'supplier' ? '/seller' : '/buyer');
    } catch (err: any) {
      if (err.data?.detail) {
        if (typeof err.data.detail === 'string') {
          showError(err.data.detail);
        } else if (Array.isArray(err.data.detail)) {
          showError(err.data.detail.map((d: any) => d.msg).join(', '));
        }
      } else {
        showError('Ошибка регистрации. Попробуйте позже.');
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white flex flex-col items-center justify-center px-4 py-8 sm:py-12">

      {/* Logo */}
      <Link to="/" className="flex items-center gap-2 mb-8">
        <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
          </svg>
        </div>
        <span className="text-xl font-bold text-gray-900">
          Цветочный<span className="text-primary-600"> маркет</span>
        </span>
      </Link>

      {/* Card */}
      <div className="w-full max-w-lg">
        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6 sm:p-8">

          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-1">Создать аккаунт</h1>
            <p className="text-sm text-gray-500">Выберите тип аккаунта и заполните данные</p>
          </div>

          {/* Role cards */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            {/* Buyer */}
            <button
              type="button"
              onClick={() => setRole('buyer')}
              className={`rounded-2xl border-2 p-4 sm:p-5 text-center cursor-pointer transition-all duration-200 ${
                role === 'buyer'
                  ? 'border-primary-300 bg-primary-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007z" />
                </svg>
              </div>
              <div className="font-semibold text-gray-900 text-sm sm:text-base mb-1">Покупатель</div>
              <div className="text-xs text-gray-500">Флорист, салон, агентство</div>
              {role === 'buyer' && (
                <div className="mt-2">
                  <div className="w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center mx-auto">
                    <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="3">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </div>
                </div>
              )}
            </button>

            {/* Supplier */}
            <button
              type="button"
              onClick={() => setRole('supplier')}
              className={`rounded-2xl border-2 p-4 sm:p-5 text-center cursor-pointer transition-all duration-200 ${
                role === 'supplier'
                  ? 'border-primary-300 bg-primary-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="w-12 h-12 bg-amber-50 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                </svg>
              </div>
              <div className="font-semibold text-gray-900 text-sm sm:text-base mb-1">Поставщик</div>
              <div className="text-xs text-gray-500">Оптовая база, питомник</div>
              {role === 'supplier' && (
                <div className="mt-2">
                  <div className="w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center mx-auto">
                    <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="3">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </div>
                </div>
              )}
            </button>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            {/* Name */}
            <Input
              label={role === 'buyer' ? 'Имя или название магазина' : 'Название компании'}
              type="text"
              placeholder={role === 'buyer' ? 'Ваше имя или название компании' : 'ООО Цветы оптом'}
              value={name}
              onChange={(e) => setName(e.target.value)}
              icon={PersonIcon}
              required
            />

            {/* Email */}
            <Input
              label="Email"
              type="email"
              placeholder="mail@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              icon={EnvelopeIcon}
              required
            />

            {/* Phone */}
            <Input
              label="Телефон"
              type="tel"
              placeholder="+7 (___) ___-__-__"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              icon={PhoneIcon}
              required
            />

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Пароль</label>
              <div className="relative">
                <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                </svg>
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Минимум 6 символов"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full pl-10 pr-10 py-2.5 border border-gray-200 rounded-xl text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showPassword ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  )}
                </button>
              </div>
              {/* Strength indicator */}
              {password && (
                <>
                  <div className="flex gap-1 mt-2">
                    {[1, 2, 3, 4].map((i) => (
                      <div
                        key={i}
                        className={`h-1 rounded-full flex-1 ${
                          i <= strength.level ? strengthColors[strength.level] : 'bg-gray-200'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-gray-400 mt-1">{strength.text}</p>
                </>
              )}
            </div>

            {/* Terms */}
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={agreedToTerms}
                onChange={(e) => setAgreedToTerms(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-primary-500 focus:ring-primary-500/20 mt-0.5 transition"
              />
              <span className="text-xs text-gray-500 leading-relaxed">
                Я принимаю{' '}
                <button type="button" className="text-primary-600 hover:text-primary-700 font-medium">условия использования</button>
                {' '}и{' '}
                <button type="button" className="text-primary-600 hover:text-primary-700 font-medium">политику конфиденциальности</button>
              </span>
            </label>

            {/* Error */}
            {errorMessage && (
              <div className={`bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3 flex items-start gap-2 ${shaking ? 'shake' : ''}`}>
                <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary-500 hover:bg-primary-600 active:scale-[0.97] text-white font-semibold py-3 rounded-xl text-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Регистрация...' : 'Зарегистрироваться'}
            </button>
          </form>

          {/* Login link */}
          <p className="text-center text-sm text-gray-500 mt-6">
            Уже есть аккаунт?{' '}
            <Link to="/login" className="text-primary-600 hover:text-primary-700 font-semibold transition-colors">
              Войти
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
