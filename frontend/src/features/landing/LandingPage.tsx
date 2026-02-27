import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';

/* ─── Mobile Menu ─── */
function MobileMenu({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  return (
    <>
      {/* Overlay */}
      <div
        className={`mobile-overlay fixed inset-0 bg-black/30 z-50 ${isOpen ? 'open' : ''}`}
        onClick={onClose}
      />
      {/* Drawer */}
      <div className={`mobile-menu-drawer fixed top-0 left-0 bottom-0 w-72 bg-white z-50 shadow-2xl ${isOpen ? 'open' : ''}`}>
        <div className="p-6">
          <div className="flex justify-between items-center mb-8">
            <span className="text-lg font-bold text-gray-900">Меню</span>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <nav className="flex flex-col gap-1">
            <a href="#how-it-works" onClick={onClose} className="px-4 py-3 text-gray-700 hover:bg-gray-50 rounded-xl transition-colors font-medium">Как это работает</a>
            <a href="#benefits" onClick={onClose} className="px-4 py-3 text-gray-700 hover:bg-gray-50 rounded-xl transition-colors font-medium">Преимущества</a>
            <a href="#for-suppliers" onClick={onClose} className="px-4 py-3 text-gray-700 hover:bg-gray-50 rounded-xl transition-colors font-medium">Поставщикам</a>
            <div className="border-t border-gray-100 my-3" />
            <Link to="/login" className="px-4 py-3 text-gray-700 hover:bg-gray-50 rounded-xl transition-colors font-medium">Войти</Link>
            <Link to="/register" className="mt-2 text-center text-white bg-primary-500 hover:bg-primary-600 px-4 py-3 rounded-xl transition-all font-medium">Регистрация</Link>
          </nav>
        </div>
      </div>
    </>
  );
}

/* ─── Fade-in Observer Hook ─── */
function useFadeInObserver() {
  useEffect(() => {
    // Small delay to ensure DOM is fully painted after React render
    const timer = setTimeout(() => {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add('visible');
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
      );

      document.querySelectorAll('.fade-in-up').forEach((el) => observer.observe(el));

      return () => observer.disconnect();
    }, 100);

    return () => clearTimeout(timer);
  }, []);
}

/* ─── Header ─── */
function LandingHeader({ onMenuOpen }: { onMenuOpen: () => void }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`fixed top-0 left-0 right-0 z-40 transition-all duration-300 ${scrolled ? 'bg-white/90 backdrop-blur-md shadow-sm' : ''}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 sm:h-20">
          {/* Logo */}
          <a href="#" className="flex items-center gap-2">
            <div className="w-9 h-9 bg-primary-500 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
              </svg>
            </div>
            <span className="text-xl font-bold text-gray-900">Цветочный<span className="text-primary-600"> маркет</span></span>
          </a>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-8">
            <a href="#how-it-works" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Как это работает</a>
            <a href="#benefits" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Преимущества</a>
            <a href="#for-suppliers" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Поставщикам</a>
          </nav>

          {/* CTA */}
          <div className="hidden md:flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-gray-700 hover:text-gray-900 px-4 py-2 transition-colors">Войти</Link>
            <Link to="/register" className="text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 active:scale-[0.97] px-5 py-2.5 rounded-xl transition-all duration-150">Регистрация</Link>
          </div>

          {/* Burger */}
          <button onClick={onMenuOpen} className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}

/* ─── Hero Section ─── */
function HeroSection() {
  return (
    <section className="hero-bg min-h-screen flex items-center relative overflow-hidden">
      {/* Decorative blobs */}
      <div className="absolute top-20 right-10 w-72 h-72 bg-primary-200/30 rounded-full blur-3xl animate-float" />
      <div className="absolute bottom-20 left-10 w-96 h-96 bg-primary-100/40 rounded-full blur-3xl animate-float-delay" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16 sm:pt-32 sm:pb-24 relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Text */}
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-2 bg-primary-50 border border-primary-200 rounded-full px-4 py-1.5 mb-6">
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium text-primary-700">B2B-платформа для цветочного бизнеса</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-gray-900 leading-[1.1] mb-6">
              Оптовые цветы для вашего бизнеса —
              <span className="text-primary-600"> в одном месте</span>
            </h1>

            <p className="text-lg sm:text-xl text-gray-600 leading-relaxed mb-8 max-w-lg">
              Сравнивайте цены от всех поставщиков города, находите лучшие предложения и заказывайте в 2 клика.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
              <Link to="/register" className="inline-flex items-center justify-center gap-2 bg-primary-500 hover:bg-primary-600 active:scale-[0.97] text-white font-semibold px-8 py-4 rounded-xl text-base transition-all duration-150 shadow-lg shadow-primary-500/25">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                </svg>
                Я покупатель
              </Link>
              <Link to="/register" className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 active:scale-[0.97] text-gray-700 font-semibold px-8 py-4 rounded-xl text-base transition-all duration-150 border border-gray-200 shadow-sm">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                </svg>
                Я поставщик
              </Link>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-8 mt-10 pt-8 border-t border-gray-200/60">
              <div>
                <div className="text-2xl sm:text-3xl font-bold text-gray-900">50+</div>
                <div className="text-sm text-gray-500">поставщиков</div>
              </div>
              <div className="w-px h-10 bg-gray-200" />
              <div>
                <div className="text-2xl sm:text-3xl font-bold text-gray-900">10 000+</div>
                <div className="text-sm text-gray-500">позиций в каталоге</div>
              </div>
              <div className="w-px h-10 bg-gray-200" />
              <div>
                <div className="text-2xl sm:text-3xl font-bold text-gray-900">0 &#8381;</div>
                <div className="text-sm text-gray-500">комиссия</div>
              </div>
            </div>
          </div>

          {/* Hero Illustration */}
          <div className="hidden lg:flex justify-center relative">
            <div className="relative w-full max-w-md">
              <div className="absolute -top-4 -left-4 w-full h-full bg-primary-100 rounded-3xl transform rotate-3" />
              <div className="relative bg-white rounded-3xl shadow-2xl p-6 transform -rotate-1">
                <div className="bg-gray-100 rounded-2xl aspect-[4/3] mb-4 overflow-hidden flex items-center justify-center">
                  <div className="text-center p-8">
                    <div className="text-6xl mb-3">&#127801;</div>
                    <div className="text-sm text-gray-400">Фото товара</div>
                  </div>
                </div>
                <div className="space-y-2">
                  <h3 className="font-semibold text-gray-900">Роза Red Naomi</h3>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-primary-600">45 &#8381;</span>
                    <span className="text-sm text-gray-400">/ шт</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>60 см</span><span>&middot;</span><span>Эквадор</span><span>&middot;</span>
                    <span className="text-primary-600 font-medium">В наличии</span>
                  </div>
                  <div className="pt-2">
                    <div className="bg-primary-500 text-white text-center py-2.5 rounded-xl text-sm font-medium">В корзину</div>
                  </div>
                </div>
              </div>

              {/* Floating badge */}
              <div className="absolute -right-6 top-8 bg-white rounded-2xl shadow-lg px-4 py-3 animate-float-delay">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary-50 rounded-xl flex items-center justify-center">
                    <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-gray-900">Заказ оформлен</div>
                    <div className="text-xs text-gray-500">3 позиции &middot; 12 400 &#8381;</div>
                  </div>
                </div>
              </div>

              {/* Floating price tag */}
              <div className="absolute -left-8 bottom-20 bg-white rounded-2xl shadow-lg px-4 py-3 animate-float-delay-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">&#127799;</span>
                  <div>
                    <div className="text-xs text-gray-500">Лучшая цена</div>
                    <div className="text-sm font-bold text-primary-600">от 28 &#8381;/шт</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce hidden sm:block">
        <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </div>
    </section>
  );
}

/* ─── Step Card ─── */
function StepCard({ num, icon, title, desc, hoverBg }: { num: string; icon: React.ReactNode; title: string; desc: string; hoverBg: string }) {
  return (
    <div className="relative group">
      <div className={`bg-gray-50 rounded-2xl p-8 ${hoverBg} transition-colors duration-300 h-full`}>
        <div className="flex items-center gap-4 mb-4">
          <span className={`text-4xl font-extrabold ${hoverBg.includes('amber') ? 'text-amber-200 group-hover:text-amber-300' : 'text-primary-200 group-hover:text-primary-300'} transition-colors`}>{num}</span>
          <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center">{icon}</div>
        </div>
        <h4 className="text-lg font-semibold text-gray-900 mb-2">{title}</h4>
        <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

/* ─── How It Works ─── */
function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-20 sm:py-28 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16 fade-in-up">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-gray-900 mb-4">Как это работает</h2>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">Три простых шага до лучших цен на цветы</p>
        </div>

        {/* For Buyers */}
        <div className="mb-20 fade-in-up">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-primary-50 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Для покупателей</h3>
          </div>
          <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
            <StepCard num="01" hoverBg="hover:bg-primary-50/50"
              icon={<svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>}
              title="Ищите цветы" desc="Умный поиск по названию, сорту, цвету и длине стебля. Фильтруйте по цене и поставщику." />
            <StepCard num="02" hoverBg="hover:bg-primary-50/50"
              icon={<svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>}
              title="Сравните цены" desc="Все поставщики города на одном экране. Видите цену за штуку, упаковку и оптовые тиры." />
            <StepCard num="03" hoverBg="hover:bg-primary-50/50"
              icon={<svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
              title="Оформите заказ" desc="Добавьте в корзину и отправьте заказ напрямую поставщику. Без посредников и комиссий." />
          </div>
        </div>

        {/* For Suppliers */}
        <div id="for-suppliers" className="fade-in-up">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-amber-50 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Для поставщиков</h3>
          </div>
          <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
            <StepCard num="01" hoverBg="hover:bg-amber-50/50"
              icon={<svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" /></svg>}
              title="Загрузите прайс" desc="Отправьте Excel или CSV файл. Система автоматически распознает позиции, цены и наличие." />
            <StepCard num="02" hoverBg="hover:bg-amber-50/50"
              icon={<svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" /></svg>}
              title="Получите заказы" desc="Покупатели находят ваш товар через каталог и отправляют заявки. Уведомления в личном кабинете." />
            <StepCard num="03" hoverBg="hover:bg-amber-50/50"
              icon={<svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" /></svg>}
              title="Растите продажи" desc="Расширяйте клиентскую базу без затрат на маркетинг. Покупатели сами вас находят." />
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Benefits Section ─── */
function BenefitsSection() {
  const benefits = [
    { title: 'Единая база цен', desc: 'Все поставщики города в одном каталоге. Больше не нужно звонить и запрашивать прайсы.', bgClass: 'bg-primary-50', textClass: 'text-primary-600', icon: <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" /> },
    { title: 'Актуальные прайсы', desc: 'Поставщики обновляют цены ежедневно. Вы всегда видите реальную стоимость и наличие.', bgClass: 'bg-sky-50', textClass: 'text-sky-600', icon: <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" /> },
    { title: 'Без комиссии', desc: 'Заказы идут напрямую поставщику. Никаких скрытых комиссий и наценок платформы.', bgClass: 'bg-amber-50', textClass: 'text-amber-600', icon: <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /> },
    { title: 'Умный поиск', desc: 'Фильтры по сорту, цвету, длине, стране. Находите именно то, что нужно вашим клиентам.', bgClass: 'bg-purple-50', textClass: 'text-purple-600', icon: <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" /> },
  ];

  return (
    <section id="benefits" className="py-20 sm:py-28 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16 fade-in-up">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-gray-900 mb-4">Почему выбирают нас</h2>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">Платформа, которая экономит время и деньги</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 fade-in-up">
          {benefits.map((b) => (
            <div key={b.title} className="bg-white rounded-2xl p-6 hover:shadow-md transition-shadow duration-200">
              <div className={`w-12 h-12 ${b.bgClass} rounded-xl flex items-center justify-center mb-4`}>
                <svg className={`w-6 h-6 ${b.textClass}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">{b.icon}</svg>
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">{b.title}</h4>
              <p className="text-sm text-gray-500 leading-relaxed">{b.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Social Proof Section ─── */
function SocialProofSection() {
  return (
    <section className="py-20 sm:py-28 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-3xl p-8 sm:p-12 lg:p-16 text-white relative overflow-hidden fade-in-up">
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-primary-500/10 rounded-full blur-3xl" />

          <div className="relative z-10 grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">Присоединяйтесь к растущему сообществу</h2>
              <p className="text-gray-400 text-lg leading-relaxed mb-8">
                Флористы и оптовые базы уже используют платформу для ежедневных закупок. Упростите свой рабочий процесс.
              </p>
              <div className="flex items-center gap-4">
                <div className="flex -space-x-3">
                  {['bg-primary-500', 'bg-sky-500', 'bg-amber-500', 'bg-purple-500'].map((bg, i) => (
                    <div key={i} className={`w-10 h-10 rounded-full ${bg} border-2 border-gray-900 flex items-center justify-center text-sm font-semibold`}>
                      {['А', 'М', 'К', 'Д'][i]}
                    </div>
                  ))}
                  <div className="w-10 h-10 rounded-full bg-gray-700 border-2 border-gray-900 flex items-center justify-center text-xs font-semibold">+46</div>
                </div>
                <span className="text-sm text-gray-400">уже на платформе</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {[
                { val: '500+', label: 'заказов в месяц' },
                { val: '50+', label: 'поставщиков' },
                { val: '10 000+', label: 'позиций' },
                { val: '24/7', label: 'доступ к каталогу' },
              ].map((s) => (
                <div key={s.label} className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 text-center">
                  <div className="text-3xl font-bold mb-1">{s.val}</div>
                  <div className="text-sm text-gray-400">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── CTA Section ─── */
function CTASection() {
  return (
    <section id="cta" className="py-20 sm:py-28 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl mx-auto text-center fade-in-up">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-gray-900 mb-4">Начните прямо сейчас</h2>
          <p className="text-lg text-gray-500 mb-10">Регистрация бесплатна. Выберите свою роль и получите доступ к платформе.</p>

          <div className="grid sm:grid-cols-2 gap-4 sm:gap-6 mb-8">
            {/* Buyer */}
            <Link to="/register" className="bg-white rounded-2xl p-8 border-2 border-gray-100 hover:border-primary-300 hover:shadow-md transition-all duration-200 group flex flex-col items-center">
              <div className="w-16 h-16 bg-primary-50 rounded-2xl flex items-center justify-center mb-4 group-hover:bg-primary-100 transition-colors">
                <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Покупатель</h3>
              <p className="text-sm text-gray-500 mb-6 text-center flex-1">Флорист, цветочный салон, event-агентство</p>
              <span className="block w-full text-center bg-primary-500 hover:bg-primary-600 active:scale-[0.97] text-white font-medium px-6 py-3 rounded-xl transition-all duration-150">Зарегистрироваться</span>
            </Link>

            {/* Supplier */}
            <Link to="/register" className="bg-white rounded-2xl p-8 border-2 border-gray-100 hover:border-amber-300 hover:shadow-md transition-all duration-200 group flex flex-col items-center">
              <div className="w-16 h-16 bg-amber-50 rounded-2xl flex items-center justify-center mb-4 group-hover:bg-amber-100 transition-colors">
                <svg className="w-8 h-8 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Поставщик</h3>
              <p className="text-sm text-gray-500 mb-6 text-center flex-1">Оптовая база, питомник, импортёр</p>
              <span className="block w-full text-center bg-amber-500 hover:bg-amber-600 active:scale-[0.97] text-white font-medium px-6 py-3 rounded-xl transition-all duration-150">Зарегистрироваться</span>
            </Link>
          </div>

          <p className="text-sm text-gray-400">Уже есть аккаунт? <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">Войти</Link></p>
        </div>
      </div>
    </section>
  );
}

/* ─── Landing Footer ─── */
function LandingFooter() {
  return (
    <footer className="bg-gray-900 text-gray-400 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
          <div className="sm:col-span-2 lg:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
              </div>
              <span className="text-white font-bold">Цветочный маркет</span>
            </div>
            <p className="text-sm leading-relaxed">B2B-платформа для оптовой торговли цветами. Все поставщики города в одном месте.</p>
          </div>
          <div>
            <h4 className="text-white font-semibold text-sm mb-4">Платформа</h4>
            <ul className="space-y-2">
              <li><Link to="/login" className="text-sm hover:text-white transition-colors">Каталог</Link></li>
              <li><a href="#how-it-works" className="text-sm hover:text-white transition-colors">Для покупателей</a></li>
              <li><a href="#for-suppliers" className="text-sm hover:text-white transition-colors">Для поставщиков</a></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold text-sm mb-4">Поддержка</h4>
            <ul className="space-y-2">
              <li><a href="#" className="text-sm hover:text-white transition-colors">Помощь</a></li>
              <li><a href="#" className="text-sm hover:text-white transition-colors">Контакты</a></li>
              <li><a href="#" className="text-sm hover:text-white transition-colors">Telegram</a></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold text-sm mb-4">Контакты</h4>
            <ul className="space-y-2">
              <li className="text-sm">info@вцвет.рф</li>
              <li className="text-sm">Telegram: @cvetmarket</li>
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-800 pt-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-xs text-gray-500">&copy; 2026 Цветочный маркет. Все права защищены.</p>
          <div className="flex gap-6">
            <a href="#" className="text-xs text-gray-500 hover:text-gray-300 transition-colors">Политика конфиденциальности</a>
            <a href="#" className="text-xs text-gray-500 hover:text-gray-300 transition-colors">Условия использования</a>
          </div>
        </div>
      </div>
    </footer>
  );
}

/* ─── Main Landing Page ─── */
export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const toggleMenu = useCallback(() => setMenuOpen((v) => !v), []);
  const closeMenu = useCallback(() => setMenuOpen(false), []);

  useFadeInObserver();

  return (
    <div className="bg-white">
      <LandingHeader onMenuOpen={toggleMenu} />
      <MobileMenu isOpen={menuOpen} onClose={closeMenu} />
      <HeroSection />
      <HowItWorksSection />
      <BenefitsSection />
      <SocialProofSection />
      <CTASection />
      <LandingFooter />
    </div>
  );
}
