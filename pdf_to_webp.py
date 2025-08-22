#!/usr/bin/env python3
"""
PDF to WebP Converter
Разделяет PDF файл на страницы и конвертирует их в WebP формат высокого качества
"""

import os
import sys
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import argparse


def pdf_to_webp(pdf_path, output_dir=None, dpi=300, quality=90, lossless=False):
    """
    Конвертирует PDF в WebP изображения
    
    Args:
        pdf_path (str): Путь к PDF файлу
        output_dir (str): Директория для сохранения (по умолчанию рядом с PDF)
        dpi (int): Разрешение в DPI (по умолчанию 300)
        quality (int): Качество WebP 0-100 (по умолчанию 90)
        lossless (bool): Использовать lossless сжатие (по умолчанию False)
    """
    
    # Проверяем существование файла
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
    
    # Определяем директорию для вывода
    pdf_file = Path(pdf_path)
    if output_dir is None:
        output_dir = pdf_file.parent / f"{pdf_file.stem}_webp"
    else:
        output_dir = Path(output_dir)
    
    # Создаем директорию если её нет
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Открываем PDF: {pdf_path}")
    
    # Открываем PDF документ
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise Exception(f"Ошибка открытия PDF: {e}")
    
    total_pages = len(doc)
    print(f"Найдено страниц: {total_pages}")
    
    # Конвертируем каждую страницу
    converted_files = []
    
    for page_num in range(total_pages):
        try:
            print(f"Обрабатываем страницу {page_num + 1}/{total_pages}...")
            
            # Получаем страницу
            page = doc[page_num]
            
            # Создаем матрицу масштабирования для нужного DPI
            # По умолчанию PyMuPDF использует 72 DPI
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            
            # Рендерим страницу в изображение
            pix = page.get_pixmap(matrix=mat)
            
            # Конвертируем в PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Имя выходного файла
            output_filename = f"{page_num + 1:02d}.webp"
            output_path = output_dir / output_filename
            
            # Сохраняем в WebP формате
            if lossless:
                img.save(output_path, 'WebP', lossless=True)
            else:
                img.save(output_path, 'WebP', quality=quality, method=6)
            
            converted_files.append(output_path)
            print(f"Сохранено: {output_path}")
            
        except Exception as e:
            print(f"Ошибка обработки страницы {page_num + 1}: {e}")
            continue
    
    # Закрываем документ
    doc.close()
    
    print(f"\nКонвертация завершена!")
    print(f"Обработано страниц: {len(converted_files)}/{total_pages}")
    print(f"Файлы сохранены в: {output_dir}")
    
    return converted_files


def main():
    parser = argparse.ArgumentParser(
        description="Конвертирует PDF в WebP изображения высокого качества"
    )
    
    parser.add_argument(
        "pdf_path",
        help="Путь к PDF файлу"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Директория для сохранения WebP файлов"
    )
    
    parser.add_argument(
        "-d", "--dpi",
        type=int,
        default=300,
        help="Разрешение в DPI (по умолчанию 300)"
    )
    
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=90,
        help="Качество WebP от 0 до 100 (по умолчанию 90)"
    )
    
    parser.add_argument(
        "-l", "--lossless",
        action="store_true",
        help="Использовать lossless сжатие WebP"
    )
    
    args = parser.parse_args()
    
    try:
        converted_files = pdf_to_webp(
            pdf_path=args.pdf_path,
            output_dir=args.output,
            dpi=args.dpi,
            quality=args.quality,
            lossless=args.lossless
        )
        
        print(f"\n✅ Успешно конвертировано {len(converted_files)} страниц!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Проверяем наличие необходимых библиотек
    try:
        import io
        import fitz  # PyMuPDF
        from PIL import Image
    except ImportError as e:
        print("❌ Не установлены необходимые библиотеки!")
        print("\nДля установки выполните:")
        print("pip install PyMuPDF Pillow")
        sys.exit(1)
    
    main()