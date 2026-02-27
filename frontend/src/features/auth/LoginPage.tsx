import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAppDispatch } from '../../hooks/useAppDispatch';
import { setCredentials } from './authSlice';
import { useLoginMutation } from './authApi';
import Input from '../../components/ui/Input';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/* ───── inline SVG icons ───── */
const EnvelopeIcon = (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
  </svg>
);

export default function LoginPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [login, { isLoading }] = useLoginMutation();

  const [role, setRole] = useState<'buyer' | 'supplier'>('buyer');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [shaking, setShaking] = useState(false);

  const showError = (msg: string) => {
    setErrorMessage(msg);
    setShaking(true);
    setTimeout(() => setShaking(false), 400);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!email || !password) {
      showError('Введите email и пароль');
      return;
    }

    try {
      const tokens = await login({ email, password, role }).unwrap();

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
        } else {
          showError('Ошибка валидации данных');
        }
      } else {
        showError('Ошибка входа. Проверьте email и пароль.');
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
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6 sm:p-8">

          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-1">Добро пожаловать</h1>
            <p className="text-sm text-gray-500">Войдите в свой аккаунт</p>
          </div>

          {/* Role tabs */}
          <div className="bg-gray-100 rounded-xl p-1 flex mb-6">
            <button
              type="button"
              onClick={() => setRole('buyer')}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-150 ${
                role === 'buyer'
                  ? 'bg-white shadow-sm text-gray-900'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Покупатель
            </button>
            <button
              type="button"
              onClick={() => setRole('supplier')}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-150 ${
                role === 'supplier'
                  ? 'bg-white shadow-sm text-gray-900'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Поставщик
            </button>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
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

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">Пароль</label>
                <button type="button" className="text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors">
                  Забыли пароль?
                </button>
              </div>
              <div className="relative">
                <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                </svg>
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;"
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
            </div>

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
              {isLoading ? 'Вход...' : 'Войти'}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-white px-3 text-xs text-gray-400">или</span>
            </div>
          </div>

          {/* Google placeholder */}
          <button
            type="button"
            disabled
            className="w-full flex items-center justify-center gap-2 border border-gray-200 hover:bg-gray-50 active:scale-[0.97] py-2.5 rounded-xl text-sm font-medium text-gray-700 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
              <path d="M6 12C6 15.3137 8.68629 18 12 18C14.6124 18 16.8349 16.3304 17.6586 14H12V10H21.8047V14H21.8C20.8734 18.5645 16.8379 22 12 22C6.47715 22 2 17.5228 2 12C2 6.47715 6.47715 2 12 2C14.7255 2 17.1962 3.09032 19.0001 4.85857L16.2426 7.61612C15.0641 6.43456 13.4159 5.7 11.6 5.7C8.50721 5.7 6 8.20721 6 12Z" fill="#4285F4"/>
            </svg>
            Войти через Google
          </button>

          {/* Register link */}
          <p className="text-center text-sm text-gray-500 mt-6">
            Нет аккаунта?{' '}
            <Link to="/register" className="text-primary-600 hover:text-primary-700 font-semibold transition-colors">
              Зарегистрируйтесь
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
