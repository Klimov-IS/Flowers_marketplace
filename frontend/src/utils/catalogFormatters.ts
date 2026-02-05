/**
 * Catalog formatting utilities for product cards
 */

// Country code to flag and name mapping
const COUNTRY_DATA: Record<string, { flag: string; name: string }> = {
  EC: { flag: '🇪🇨', name: 'Эквадор' },
  NL: { flag: '🇳🇱', name: 'Нидерланды' },
  CO: { flag: '🇨🇴', name: 'Колумбия' },
  KE: { flag: '🇰🇪', name: 'Кения' },
  RU: { flag: '🇷🇺', name: 'Россия' },
  BY: { flag: '🇧🇾', name: 'Беларусь' },
  ZA: { flag: '🇿🇦', name: 'ЮАР' },
  IT: { flag: '🇮🇹', name: 'Италия' },
  IL: { flag: '🇮🇱', name: 'Израиль' },
  ET: { flag: '🇪🇹', name: 'Эфиопия' },
};

// Pack type translations
const PACK_TYPE_LABELS: Record<string, string> = {
  bak: 'Бак',
  pack: 'Упак',
  bunch: 'Пучок',
};

/**
 * Get country flag emoji by country code
 */
export function getCountryFlag(code: string | null | undefined): string {
  if (!code) return '';
  return COUNTRY_DATA[code.toUpperCase()]?.flag || '';
}

/**
 * Get country name by country code
 */
export function getCountryName(code: string | null | undefined): string {
  if (!code) return '';
  return COUNTRY_DATA[code.toUpperCase()]?.name || code;
}

/**
 * Format country display: "🇪🇨 Эквадор"
 */
export function formatCountry(code: string | null | undefined): string {
  if (!code) return '';
  const data = COUNTRY_DATA[code.toUpperCase()];
  if (!data) return code;
  return `${data.flag} ${data.name}`;
}

/**
 * Format pack info: "Бак 25 шт"
 */
export function formatPackInfo(
  packType: string | null | undefined,
  packQty: number | null | undefined
): string {
  if (!packType && !packQty) return '';

  const type = packType ? PACK_TYPE_LABELS[packType.toLowerCase()] || packType : '';
  const qty = packQty ? `${packQty} шт` : '';

  return [type, qty].filter(Boolean).join(' ');
}

/**
 * Format tier info: "от 50 шт" or "10–50 шт"
 */
export function formatTier(
  tierMin: number | null | undefined,
  tierMax: number | null | undefined
): string {
  if (!tierMin && !tierMax) return '';
  if (tierMin && !tierMax) return `от ${tierMin} шт`;
  if (!tierMin && tierMax) return `до ${tierMax} шт`;
  return `${tierMin}–${tierMax} шт`;
}

/**
 * Format colors as comma-separated string
 */
export function formatColors(colors: string[] | null | undefined): string {
  if (!colors || colors.length === 0) return '';
  return colors.join(', ');
}
