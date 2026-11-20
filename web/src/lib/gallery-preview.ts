// При переполнении шестое место занимает превью первого скрытого кадра с +N.
export function thumbnailWindow<T>(items: T[], limit = 6): {visible: T[]; hidden: T[]} {
  return items.length > limit ? {visible: items.slice(0, limit - 1), hidden: items.slice(limit - 1)} : {visible: items, hidden: []};
}
