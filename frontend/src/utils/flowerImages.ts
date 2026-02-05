/**
 * Mapping flower types to image paths.
 * MVP: One image per flower type.
 */

// Canonical flower type name → image filename
const FLOWER_TYPE_TO_SLUG: Record<string, string> = {
  // Русские названия (из attributes.flower_type)
  'Роза': 'rosa',
  'Гвоздика': 'carnation',
  'Гипсофила': 'gypsophila',
  'Рускус': 'ruscus',
  'Альстромерия': 'alstroemeria',
  'Писташ': 'pistache',
  'Протея': 'protea',
  'Эвкалипт': 'eucalyptus',
  // English names (fallback from product_type)
  'rose': 'rosa',
  'carnation': 'carnation',
  'gypsophila': 'gypsophila',
  'ruscus': 'ruscus',
  'alstroemeria': 'alstroemeria',
  'pistache': 'pistache',
  'protea': 'protea',
  'eucalyptus': 'eucalyptus',
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

  const slug = FLOWER_TYPE_TO_SLUG[flowerType]
    || FLOWER_TYPE_TO_SLUG[flowerType.toLowerCase()];

  if (slug) {
    return `${BASE_PATH}/${slug}.jpg.png`;
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
  return flowerType in FLOWER_TYPE_TO_SLUG || flowerType.toLowerCase() in FLOWER_TYPE_TO_SLUG;
}
