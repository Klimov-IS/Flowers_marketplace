// Color mapping for flower colors
const COLORS: Record<string, string> = {
  'белый': '#ffffff',
  'красный': '#e53935',
  'розовый': '#ec407a',
  'жёлтый': '#fdd835',
  'желтый': '#fdd835',
  'оранжевый': '#ff9800',
  'фиолетовый': '#9c27b0',
  'синий': '#1e88e5',
  'голубой': '#42a5f5',
  'зелёный': '#43a047',
  'зеленый': '#43a047',
  'персиковый': '#ffab91',
  'кремовый': '#fff8e1',
  'бордовый': '#880e4f',
  'лавандовый': '#ce93d8',
  'коралловый': '#ff7043',
  'микс': 'linear-gradient(135deg, #e53935 0%, #fdd835 25%, #43a047 50%, #1e88e5 75%, #9c27b0 100%)',
  '—': '#e0e0e0',
};

interface ColorSquaresProps {
  colors: string[];
}

export default function ColorSquares({ colors }: ColorSquaresProps) {
  if (!colors || colors.length === 0) {
    return <span className="text-gray-400">—</span>;
  }

  return (
    <div className="flex items-center gap-1">
      {colors.map((color, index) => {
        const colorValue = COLORS[color.toLowerCase()] || COLORS['—'];
        const isGradient = colorValue.includes('gradient');
        const displayName = color.charAt(0).toUpperCase() + color.slice(1);

        return (
          <span
            key={index}
            title={displayName}
            className="
              w-4 h-4 rounded-sm border border-gray-300
              cursor-default transition-transform hover:scale-125 hover:z-10
            "
            style={
              isGradient
                ? { background: colorValue }
                : { backgroundColor: colorValue }
            }
          />
        );
      })}
    </div>
  );
}
