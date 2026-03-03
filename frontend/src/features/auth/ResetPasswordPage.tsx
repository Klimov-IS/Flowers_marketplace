import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  useForgotPasswordMutation,
  useVerifyResetCodeMutation,
  useResetPasswordMutation,
} from './authApi';
import Input from '../../components/ui/Input';

/* ───── icons ───── */
const EnvelopeIcon = (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
  </svg>
);

/* ───── password strength (reused from RegisterPage) ───── */
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

/* ───── helpers ───── */
function formatSeconds(s: number) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

function extractError(err: any): string {
  if (err?.data?.detail) {
    if (typeof err.data.detail === 'string') return err.data.detail;
    if (Array.isArray(err.data.detail)) return err.data.detail.map((d: any) => d.msg).join(', ');
  }
  return 'Произошла ошибка. Попробуйте позже.';
}

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [forgotPassword, { isLoading: isSending }] = useForgotPasswordMutation();
  const [verifyResetCode, { isLoading: isVerifying }] = useVerifyResetCodeMutation();
  const [resetPassword, { isLoading: isResetting }] = useResetPasswordMutation();

  // Shared state
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [role, setRole] = useState<'buyer' | 'supplier'>('buyer');
  const [email, setEmail] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [shaking, setShaking] = useState(false);

  // Step 2 state
  const [code, setCode] = useState('');
  const [expiresIn, setExpiresIn] = useState(600);
  const [resendCooldown, setResendCooldown] = useState(0);

  // Step 3 state
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const strength = useMemo(() => getPasswordStrength(newPassword), [newPassword]);

  const showError = useCallback((msg: string) => {
    setErrorMessage(msg);
    setShaking(true);
    setTimeout(() => setShaking(false), 400);
  }, []);

  // Countdown timers
  useEffect(() => {
    if (step !== 2) return;
    if (expiresIn <= 0) return;
    const t = setInterval(() => setExpiresIn((v) => Math.max(0, v - 1)), 1000);
    return () => clearInterval(t);
  }, [step, expiresIn]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setInterval(() => setResendCooldown((v) => Math.max(0, v - 1)), 1000);
    return () => clearInterval(t);
  }, [resendCooldown]);

  /* ───── Step 1: request code ───── */
  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    if (!email) { showError('Введите email'); return; }

    try {
      const resp = await forgotPassword({ email, role }).unwrap();
      setExpiresIn(resp.expires_in);
      setResendCooldown(60);
      setCode('');
      setStep(2);
    } catch (err) {
      showError(extractError(err));
    }
  };

  /* ───── Step 2: verify code ───── */
  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    if (code.length !== 6) { showError('Введите 6-значный код'); return; }

    try {
      const resp = await verifyResetCode({ email, role, code }).unwrap();
      setResetToken(resp.reset_token);
      setStep(3);
    } catch (err) {
      showError(extractError(err));
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;
    setErrorMessage('');
    try {
      const resp = await forgotPassword({ email, role }).unwrap();
      setExpiresIn(resp.expires_in);
      setResendCooldown(60);
      setCode('');
    } catch (err) {
      showError(extractError(err));
    }
  };

  /* ───── Step 3: new password ───── */
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    if (newPassword.length < 6) { showError('Пароль должен быть минимум 6 символов'); return; }
    if (newPassword !== confirmPassword) { showError('Пароли не совпадают'); return; }

    try {
      await resetPassword({ reset_token: resetToken, new_password: newPassword }).unwrap();
      navigate('/login', { state: { message: 'Пароль успешно изменён. Войдите с новым паролем.' } });
    } catch (err) {
      showError(extractError(err));
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
          Вцвет<span className="text-primary-600"> маркет</span>
        </span>
      </Link>

      {/* Card */}
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6 sm:p-8">
          {/* Progress dots */}
          <div className="flex items-center justify-center gap-2 mb-6">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`h-2 rounded-full transition-all duration-300 ${
                  s === step ? 'w-8 bg-primary-500' : s < step ? 'w-2 bg-primary-300' : 'w-2 bg-gray-200'
                }`}
              />
            ))}
          </div>

          {/* ═══ STEP 1: Email ═══ */}
          {step === 1 && (
            <>
              <div className="text-center mb-6">
                <div className="w-14 h-14 bg-primary-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-7 h-7 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-gray-900 mb-1">Восстановление пароля</h1>
                <p className="text-sm text-gray-500">Мы отправим код подтверждения в Telegram</p>
              </div>

              {/* Role tabs */}
              <div className="bg-gray-100 rounded-xl p-1 flex mb-6">
                <button
                  type="button"
                  onClick={() => setRole('buyer')}
                  className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-150 ${
                    role === 'buyer' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Покупатель
                </button>
                <button
                  type="button"
                  onClick={() => setRole('supplier')}
                  className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-150 ${
                    role === 'supplier' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Поставщик
                </button>
              </div>

              <form onSubmit={handleRequestCode} className="space-y-4">
                <Input
                  label="Email"
                  type="email"
                  placeholder="mail@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  icon={EnvelopeIcon}
                  required
                />

                {errorMessage && (
                  <div className={`bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3 flex items-start gap-2 ${shaking ? 'shake' : ''}`}>
                    <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                    </svg>
                    <span>{errorMessage}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSending}
                  className="w-full bg-primary-500 hover:bg-primary-600 active:scale-[0.97] text-white font-semibold py-3 rounded-xl text-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSending ? 'Отправка...' : 'Отправить код'}
                </button>
              </form>
            </>
          )}

          {/* ═══ STEP 2: Code ═══ */}
          {step === 2 && (
            <>
              <div className="text-center mb-6">
                <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-7 h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-gray-900 mb-1">Введите код</h1>
                <p className="text-sm text-gray-500">
                  Код отправлен в Telegram на аккаунт <span className="font-medium text-gray-700">{email}</span>
                </p>
              </div>

              <form onSubmit={handleVerifyCode} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Код из Telegram</label>
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    placeholder="000000"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    className="w-full text-center text-2xl tracking-[0.5em] font-mono py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
                    autoFocus
                  />
                </div>

                {/* Timer */}
                <div className="flex items-center justify-between text-sm">
                  <span className={`${expiresIn <= 60 ? 'text-red-500' : 'text-gray-400'}`}>
                    {expiresIn > 0 ? `Код действует: ${formatSeconds(expiresIn)}` : 'Код истёк'}
                  </span>
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={resendCooldown > 0 || isSending}
                    className="text-primary-600 hover:text-primary-700 font-medium disabled:text-gray-300 disabled:cursor-not-allowed transition-colors"
                  >
                    {resendCooldown > 0 ? `Повторить (${resendCooldown}с)` : 'Отправить повторно'}
                  </button>
                </div>

                {errorMessage && (
                  <div className={`bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3 flex items-start gap-2 ${shaking ? 'shake' : ''}`}>
                    <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                    </svg>
                    <span>{errorMessage}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isVerifying || code.length !== 6}
                  className="w-full bg-primary-500 hover:bg-primary-600 active:scale-[0.97] text-white font-semibold py-3 rounded-xl text-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isVerifying ? 'Проверка...' : 'Подтвердить'}
                </button>

                <button
                  type="button"
                  onClick={() => { setStep(1); setErrorMessage(''); }}
                  className="w-full text-sm text-gray-500 hover:text-gray-700 font-medium transition-colors"
                >
                  Изменить email
                </button>
              </form>
            </>
          )}

          {/* ═══ STEP 3: New password ═══ */}
          {step === 3 && (
            <>
              <div className="text-center mb-6">
                <div className="w-14 h-14 bg-green-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-7 h-7 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-gray-900 mb-1">Новый пароль</h1>
                <p className="text-sm text-gray-500">Придумайте новый пароль для вашего аккаунта</p>
              </div>

              <form onSubmit={handleResetPassword} className="space-y-4">
                {/* New password */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Новый пароль</label>
                  <div className="relative">
                    <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                    </svg>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Минимум 6 символов"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
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
                  {newPassword && (
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

                {/* Confirm password */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Подтвердите пароль</label>
                  <div className="relative">
                    <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                    </svg>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Повторите пароль"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      className={`w-full pl-10 pr-4 py-2.5 border rounded-xl text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all ${
                        confirmPassword && confirmPassword !== newPassword
                          ? 'border-red-300'
                          : 'border-gray-200'
                      }`}
                    />
                  </div>
                  {confirmPassword && confirmPassword !== newPassword && (
                    <p className="text-xs text-red-500 mt-1">Пароли не совпадают</p>
                  )}
                </div>

                {errorMessage && (
                  <div className={`bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3 flex items-start gap-2 ${shaking ? 'shake' : ''}`}>
                    <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                    </svg>
                    <span>{errorMessage}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isResetting}
                  className="w-full bg-primary-500 hover:bg-primary-600 active:scale-[0.97] text-white font-semibold py-3 rounded-xl text-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isResetting ? 'Сохранение...' : 'Сменить пароль'}
                </button>
              </form>
            </>
          )}

          {/* Back to login */}
          <p className="text-center text-sm text-gray-500 mt-6">
            <Link to="/login" className="text-primary-600 hover:text-primary-700 font-semibold transition-colors">
              Вернуться ко входу
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
