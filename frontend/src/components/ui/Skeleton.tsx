interface SkeletonProps {
  className?: string;
  width?: string;
  height?: string;
  rounded?: string;
  variant?: 'default' | 'text' | 'title' | 'image' | 'button';
}

export default function Skeleton({
  className = '',
  width,
  height,
  rounded = 'rounded-xl',
  variant = 'default',
}: SkeletonProps) {
  const variants = {
    default: '',
    text: 'h-4',
    title: 'h-6',
    image: 'aspect-[4/5]',
    button: 'h-10 rounded-xl',
  };

  const variantRounded = variant === 'button' ? 'rounded-xl' : rounded;

  return (
    <div
      className={`bg-gray-200 animate-pulse ${variantRounded} ${variants[variant]} ${className}`}
      style={{ width, height }}
    />
  );
}
