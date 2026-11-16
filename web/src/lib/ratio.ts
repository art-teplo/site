// "4 / 3" → 1.333…: пропорция рамки из записи CSS aspect-ratio
export const ratioValue = (ratio: string) => {
  const [w, h] = ratio.split("/").map((n) => Number(n.trim()));
  return w / h;
};
