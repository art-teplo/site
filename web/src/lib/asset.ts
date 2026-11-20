// Версия картинок в адресе. Оптимизатор Next отдаёт их с кэшем на 4 часа и не умеет сбрасывать его,
// поэтому после замены файлов в public/images увеличьте число — браузеры запросят картинки заново.
export const IMAGES_VERSION = "4";

// Только своим файлам из public/images: фото из админки при замене получают новое имя
export const versioned = (src: string) => (src.startsWith("/") ? `${src}?v=${IMAGES_VERSION}` : src);
