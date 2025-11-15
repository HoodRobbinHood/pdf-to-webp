#!/usr/bin/env python3
"""
PDF to WebP Converter

Разделяет PDF файл на страницы и конвертирует их в WebP формат высокого качества.
Поддерживает автоматическую обработку одного файла или интерактивный выбор из нескольких.
"""

import argparse
import io
import logging
import sys
from pathlib import Path
from typing import List, Optional

try:
    import fitz  # PyMuPDF
    from PIL import Image
except ImportError as e:
    print("❌ Не установлены необходимые библиотеки!")
    print("\nДля установки выполните:")
    print("pip install PyMuPDF Pillow")
    sys.exit(1)


# Константы
DEFAULT_DPI = 300
DEFAULT_QUALITY = 90
DEFAULT_ZOOM_BASE = 72.0
WEBP_METHOD = 6

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def find_pdf_files(directory: Path) -> List[Path]:
    """
    Находит все PDF файлы в указанной директории.

    Args:
        directory: Путь к директории для поиска.

    Returns:
        Список путей к найденным PDF файлам, отсортированный по имени.

    Raises:
        ValueError: Если переданный путь не является директорией.
    """
    if not directory.is_dir():
        raise ValueError(f"Путь не является директорией: {directory}")

    pdf_files = sorted(directory.glob("*.pdf"))
    logger.debug(f"Найдено PDF файлов в {directory}: {len(pdf_files)}")
    return pdf_files


def interactive_file_selection(pdf_files: List[Path]) -> Path:
    """
    Предоставляет интерактивный выбор PDF файла из списка.

    Args:
        pdf_files: Список путей к PDF файлам.

    Returns:
        Выбранный путь к PDF файлу.

    Raises:
        ValueError: Если список файлов пуст.
        KeyboardInterrupt: Если пользователь прервал выбор.
    """
    if not pdf_files:
        raise ValueError("Список PDF файлов пуст")

    print("\nНайдено несколько PDF файлов:")
    print("-" * 60)
    for idx, pdf_file in enumerate(pdf_files, start=1):
        file_size = pdf_file.stat().st_size / (1024 * 1024)  # MB
        print(f"  {idx}. {pdf_file.name} ({file_size:.2f} MB)")
    print("-" * 60)

    while True:
        try:
            choice = input(f"\nВыберите файл (1-{len(pdf_files)}) или 'q' для выхода: ").strip()

            if choice.lower() == 'q':
                raise KeyboardInterrupt("Пользователь прервал выбор файла")

            choice_num = int(choice)
            if 1 <= choice_num <= len(pdf_files):
                selected_file = pdf_files[choice_num - 1]
                logger.info(f"Выбран файл: {selected_file.name}")
                return selected_file
            else:
                print(f"❌ Пожалуйста, введите число от 1 до {len(pdf_files)}")
        except ValueError:
            print("❌ Пожалуйста, введите корректное число или 'q' для выхода")
        except KeyboardInterrupt:
            print("\n\nОперация отменена пользователем")
            raise


def validate_parameters(dpi: int, quality: int) -> None:
    """
    Валидирует параметры конвертации.

    Args:
        dpi: Разрешение в DPI.
        quality: Качество WebP от 0 до 100.

    Raises:
        ValueError: Если параметры выходят за допустимые пределы.
    """
    if dpi < 72 or dpi > 1200:
        raise ValueError(f"DPI должен быть в диапазоне 72-1200, получено: {dpi}")

    if quality < 0 or quality > 100:
        raise ValueError(f"Качество должно быть в диапазоне 0-100, получено: {quality}")


def pdf_to_webp(
    pdf_path: Path,
    output_dir: Optional[Path] = None,
    dpi: int = DEFAULT_DPI,
    quality: int = DEFAULT_QUALITY,
    lossless: bool = False
) -> List[Path]:
    """
    Конвертирует PDF в WebP изображения.

    Каждая страница PDF сохраняется как отдельный WebP файл с нумерацией 01.webp, 02.webp и т.д.

    Args:
        pdf_path: Путь к PDF файлу.
        output_dir: Директория для сохранения WebP файлов. Если не указана,
                   создается директория с именем {имя_файла}_webp рядом с PDF.
        dpi: Разрешение в DPI для рендеринга страниц. По умолчанию 300.
        quality: Качество WebP сжатия от 0 до 100. По умолчанию 90.
                Игнорируется, если lossless=True.
        lossless: Использовать lossless сжатие WebP. По умолчанию False.

    Returns:
        Список путей к созданным WebP файлам.

    Raises:
        FileNotFoundError: Если PDF файл не найден.
        ValueError: Если параметры некорректны.
        RuntimeError: Если произошла ошибка при обработке PDF.
    """
    # Валидация входных параметров
    validate_parameters(dpi, quality)

    # Проверка существования файла
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")

    if not pdf_path.is_file():
        raise ValueError(f"Указанный путь не является файлом: {pdf_path}")

    # Определение директории для вывода
    if output_dir is None:
        output_dir = pdf_path.parent / f"{pdf_path.stem}_webp"
    else:
        output_dir = Path(output_dir)

    # Создание директории для вывода
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Выходная директория: {output_dir}")

    logger.info(f"Открываем PDF: {pdf_path}")

    # Открытие PDF документа
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        raise RuntimeError(f"Ошибка открытия PDF файла: {e}") from e

    try:
        total_pages = len(doc)
        logger.info(f"Найдено страниц: {total_pages}")

        if total_pages == 0:
            raise ValueError("PDF файл не содержит страниц")

        # Конвертация каждой страницы
        converted_files: List[Path] = []
        zoom = dpi / DEFAULT_ZOOM_BASE
        matrix = fitz.Matrix(zoom, zoom)

        for page_num in range(total_pages):
            try:
                logger.info(f"Обрабатываем страницу {page_num + 1}/{total_pages}...")

                # Получение страницы
                page = doc[page_num]

                # Рендеринг страницы в изображение
                pix = page.get_pixmap(matrix=matrix)

                # Конвертация в PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                # Формирование имени выходного файла
                output_filename = f"{page_num + 1:02d}.webp"
                output_path = output_dir / output_filename

                # Сохранение в WebP формате
                if lossless:
                    img.save(output_path, 'WebP', lossless=True)
                else:
                    img.save(output_path, 'WebP', quality=quality, method=WEBP_METHOD)

                converted_files.append(output_path)
                logger.debug(f"Сохранено: {output_path}")

            except Exception as e:
                logger.error(f"Ошибка обработки страницы {page_num + 1}: {e}")
                continue

        logger.info(f"Конвертация завершена!")
        logger.info(f"Обработано страниц: {len(converted_files)}/{total_pages}")
        logger.info(f"Файлы сохранены в: {output_dir}")

        if len(converted_files) == 0:
            raise RuntimeError("Не удалось обработать ни одной страницы")

        return converted_files

    finally:
        doc.close()


def resolve_pdf_path(pdf_path_arg: Optional[str]) -> Path:
    """
    Разрешает путь к PDF файлу с учетом умной обработки.

    Если путь не указан, ищет PDF файлы в текущей директории и либо
    возвращает единственный найденный, либо предлагает выбор.

    Args:
        pdf_path_arg: Путь к PDF файлу из аргументов командной строки.

    Returns:
        Путь к выбранному PDF файлу.

    Raises:
        FileNotFoundError: Если PDF файлы не найдены или указанный файл не существует.
    """
    current_dir = Path.cwd()

    # Если путь указан явно
    if pdf_path_arg:
        pdf_path = Path(pdf_path_arg)
        if not pdf_path.exists():
            raise FileNotFoundError(
                f"Указанный PDF файл не найден: {pdf_path}\n"
                f"Текущая директория: {current_dir}"
            )
        return pdf_path.resolve()

    # Поиск PDF файлов в текущей директории
    logger.info(f"Поиск PDF файлов в директории: {current_dir}")
    pdf_files = find_pdf_files(current_dir)

    if not pdf_files:
        raise FileNotFoundError(
            f"PDF файлы не найдены в текущей директории: {current_dir}\n"
            f"Укажите путь к PDF файлу или поместите PDF файл в текущую директорию."
        )

    if len(pdf_files) == 1:
        selected_file = pdf_files[0]
        logger.info(f"Найден один PDF файл, используем: {selected_file.name}")
        return selected_file.resolve()

    # Несколько файлов - интерактивный выбор
    return interactive_file_selection(pdf_files).resolve()


def main() -> None:
    """Главная функция для запуска конвертера из командной строки."""
    parser = argparse.ArgumentParser(
        description="Конвертирует PDF в WebP изображения высокого качества",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s document.pdf
  %(prog)s document.pdf -o output_folder
  %(prog)s document.pdf -d 600 -q 95
  %(prog)s document.pdf --lossless
  %(prog)s                    # Автоматический поиск PDF в текущей директории
        """
    )

    parser.add_argument(
        "pdf_path",
        nargs='?',
        help="Путь к PDF файлу (опционально, если не указан - поиск в текущей директории)"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Директория для сохранения WebP файлов"
    )

    parser.add_argument(
        "-d", "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Разрешение в DPI (по умолчанию {DEFAULT_DPI})"
    )

    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=DEFAULT_QUALITY,
        help=f"Качество WebP от 0 до 100 (по умолчанию {DEFAULT_QUALITY})"
    )

    parser.add_argument(
        "-l", "--lossless",
        action="store_true",
        help="Использовать lossless сжатие WebP"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Включить подробный вывод (debug режим)"
    )

    args = parser.parse_args()

    # Настройка уровня логирования
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Разрешение пути к PDF
        pdf_path = resolve_pdf_path(args.pdf_path)

        # Определение выходной директории
        output_dir = Path(args.output) if args.output else None

        # Конвертация
        converted_files = pdf_to_webp(
            pdf_path=pdf_path,
            output_dir=output_dir,
            dpi=args.dpi,
            quality=args.quality,
            lossless=args.lossless
        )

        print(f"\n✅ Успешно конвертировано {len(converted_files)} страниц!")
        print(f"📁 Файлы сохранены в: {converted_files[0].parent}")

    except (FileNotFoundError, ValueError, RuntimeError) as e:
        logger.error(f"Ошибка: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Операция прервана пользователем")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
