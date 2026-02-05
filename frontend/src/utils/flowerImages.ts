/**
 * Mapping flower types to image paths.
 * Images stored with Russian names matching product_type from database.
 */

// All available flower images (Russian names matching filenames)
const AVAILABLE_IMAGES = new Set([
  'Роза',
  'Гвоздика',
  'Гипсофила',
  'Рускус',
  'Альстромерия',
  'Писташ',
  'Эвкалипт',
  // Дополнительные изображения
  'Анемон',
  'Аспидистра',
  'Астильба',
  'Гербера',
  'Ирис',
  'Камилла (ромашка кустовая)',
  'Лилия',
  'Маттиола',
  'Пион',
  'Ранункулюс',
  'Салал',
  'Статица (Лимониум)',
  'Тюльпан',
  'Хризантема',
  'Эустома (Лизиантус)',
]);

// Fallback mapping for English names → Russian filenames
const ENGLISH_TO_RUSSIAN: Record<string, string> = {
  'rose': 'Роза',
  'carnation': 'Гвоздика',
  'gypsophila': 'Гипсофила',
  'ruscus': 'Рускус',
  'alstroemeria': 'Альстромерия',
  'pistache': 'Писташ',
  'eucalyptus': 'Эвкалипт',
  'protea': 'Протея', // No image yet, will fall back to default
  'anemone': 'Анемон',
  'aspidistra': 'Аспидистра',
  'astilbe': 'Астильба',
  'gerbera': 'Гербера',
  'iris': 'Ирис',
  'lily': 'Лилия',
  'matthiola': 'Маттиола',
  'peony': 'Пион',
  'ranunculus': 'Ранункулюс',
  'tulip': 'Тюльпан',
  'chrysanthemum': 'Хризантема',
  'eustoma': 'Эустома (Лизиантус)',
};

// Base path includes /flower prefix for production nginx routing
const BASE_PATH = '/flower/images/flowers';
const DEFAULT_IMAGE = `${BASE_PATH}/default.jpg.png`;

/**
 * Get flower image URL by flower type name.
 * @param flowerType - Russian or English flower type name
 * @returns Image URL
 */
export function getFlowerImage(flowerType: string | undefined | null): string {
  if (!flowerType) return DEFAULT_IMAGE;

  // Try direct Russian name match
  if (AVAILABLE_IMAGES.has(flowerType)) {
    return `${BASE_PATH}/${encodeURIComponent(flowerType)}.png`;
  }

  // Try English → Russian mapping
  const russianName = ENGLISH_TO_RUSSIAN[flowerType.toLowerCase()];
  if (russianName && AVAILABLE_IMAGES.has(russianName)) {
    return `${BASE_PATH}/${encodeURIComponent(russianName)}.png`;
  }

  return DEFAULT_IMAGE;
}

/**
 * Get default flower image.
 */
export function getDefaultFlowerImage(): string {
  return DEFAULT_IMAGE;
}

/**
 * Check if flower type has a dedicated image.
 */
export function hasFlowerImage(flowerType: string | undefined | null): boolean {
  if (!flowerType) return false;
  return AVAILABLE_IMAGES.has(flowerType)
    || (flowerType.toLowerCase() in ENGLISH_TO_RUSSIAN
        && AVAILABLE_IMAGES.has(ENGLISH_TO_RUSSIAN[flowerType.toLowerCase()]));
}
