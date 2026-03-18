"""PDF processing module for downloading and extracting images."""

import os
import requests
import fitz  # PyMuPDF
import time
from typing import List, Dict, Tuple
from pathlib import Path

from .config import config


class PDFProcessor:
    """Handles PDF downloading and image extraction."""

    def __init__(self):
        """Initialize PDF processor with configuration."""
        self.pdf_config = config.get_pdf_config()
        self.download_config = self.pdf_config.get('download', {})
        self.image_config = self.pdf_config.get('image_extraction', {})

    def download_pdf(self, paper: Dict, output_dir: str) -> str:
        """Download PDF from ArXiv.

        Args:
            paper: Paper metadata dict
            output_dir: Output directory

        Returns:
            Path to downloaded PDF
        """
        pdf_url = paper['pdf_url']
        filename = f"{paper['id']}.pdf"
        file_path = os.path.join(output_dir, filename)

        if os.path.exists(file_path):
            print(f"PDF already exists: {filename}")
            return file_path

        try:
            print(f"Downloading PDF: {filename}")

            headers = {
                'User-Agent': self.download_config.get('user_agent', 'ArXiv-Summarizer-Bot/1.0')
            }

            timeout = self.download_config.get('timeout', 30)
            retry_attempts = self.download_config.get('retry_attempts', 3)

            for attempt in range(retry_attempts):
                try:
                    response = requests.get(pdf_url, headers=headers, timeout=timeout, stream=True)
                    response.raise_for_status()

                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    print(f"✅ Downloaded: {filename}")
                    return file_path

                except Exception as e:
                    print(f"❌ Download attempt {attempt + 1} failed: {e}")
                    if attempt < retry_attempts - 1:
                        time.sleep(2)
                    else:
                        raise

        except Exception as e:
            print(f"❌ Failed to download PDF {filename}: {e}")
            return None

    def extract_images(self, pdf_path: str, paper_id: str, output_dir: str) -> List[str]:
        """Extract architecture figures from PDF.

        Args:
            pdf_path: Path to PDF file
            paper_id: Paper identifier
            output_dir: Output directory for images

        Returns:
            List of extracted image paths
        """
        if not self.image_config.get('enabled', True):
            return []

        try:
            doc = fitz.open(pdf_path)
            images_dir = os.path.join(output_dir, paper_id)
            os.makedirs(images_dir, exist_ok=True)

            # Try page screenshot approach first
            screenshot_images = self._extract_by_screenshot(doc, paper_id, images_dir)
            if screenshot_images:
                doc.close()
                print(f"Extracted {len(screenshot_images)} architecture figures using screenshots")
                return screenshot_images

            print("Screenshot approach failed, falling back to direct image extraction")

            # Fallback to direct image extraction from PDF
            extracted_images = self._extract_direct_images(doc, paper_id, images_dir)

            doc.close()
            print(f"Extracted {len(extracted_images)} images using direct extraction")
            return extracted_images

        except Exception as e:
            print(f"Error extracting images from {pdf_path}: {e}")
            return []

    def _extract_by_screenshot(self, doc, paper_id: str, images_dir: str) -> List[str]:
        """Extract images using page screenshot approach."""
        screenshot_images = []

        for page_num in range(min(10, len(doc))):  # Check first 10 pages
            page = doc[page_num]
            text = page.get_text().lower()

            if not self._is_architecture_page(text):
                continue

            print(f"  Processing page {page_num + 1}...")

            figure_areas = self._detect_figure_areas(page, text)
            if figure_areas:
                print(f"    Detected architecture page: page {page_num+1}, found {len(figure_areas)} figure areas")

                zoom = self.image_config.get('zoom_factor', 3.0)
                mat = fitz.Matrix(zoom, zoom)

                for i, area in enumerate(figure_areas):
                    try:
                        clip_rect = fitz.Rect(area['bbox'])
                        figure_pix = page.get_pixmap(matrix=mat, clip=clip_rect)

                        min_size = self.image_config.get('min_image_size', [200, 150])
                        if figure_pix.width > min_size[0] and figure_pix.height > min_size[1]:
                            img_filename = f"{paper_id}_page_{page_num+1}_figure_{i+1}.png"
                            img_path = os.path.join(images_dir, img_filename)
                            figure_pix.save(img_path)
                            screenshot_images.append(img_path)
                            print(f"      Saved figure: {img_filename} ({figure_pix.width}x{figure_pix.height})")

                        figure_pix = None
                    except Exception as e:
                        print(f"      Failed to extract figure {i+1}: {e}")

                if len(screenshot_images) >= 5:  # Limit number of images
                    break

        return screenshot_images

    def _is_architecture_page(self, text_content: str) -> bool:
        """Check if page contains architecture-related content."""
        keywords = config.get('pdf.image_extraction.figure_keywords.high_value', []) + \
                  config.get('pdf.image_extraction.figure_keywords.general', [])

        negative_keywords = config.get('pdf.image_extraction.figure_keywords.negative', [])

        # Skip pages with negative keywords
        if any(neg in text_content for neg in negative_keywords):
            return False

        # Check for positive keywords
        return any(keyword in text_content for keyword in keywords)

    def _detect_figure_areas(self, page, text_content: str) -> List[Dict]:
        """Detect figure areas in the page."""
        try:
            figure_areas = []
            image_list = page.get_images(full=True)

            if not image_list:
                return []

            # Collect valid images
            valid_images = []
            min_size = self.image_config.get('min_image_size', [80, 80])

            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(page.parent, xref)

                    if pix.width > min_size[0] and pix.height > min_size[1]:
                        # Get image position
                        if len(img) >= 6:
                            raw_bbox = img[2:6]
                            try:
                                img_bbox = tuple(float(x) for x in raw_bbox)
                            except (ValueError, TypeError):
                                img_bbox = (100.0, 100.0, 400.0, 300.0)
                        else:
                            img_bbox = (100.0, 100.0, 400.0, 300.0)

                        valid_images.append({
                            'index': img_index,
                            'bbox': img_bbox,
                            'size': (pix.width, pix.height)
                        })

                    pix = None
                except Exception:
                    continue

            if not valid_images:
                return []

            # Create combined figure area
            if len(valid_images) > 1:
                all_x0 = min(img['bbox'][0] for img in valid_images)
                all_y0 = min(img['bbox'][1] for img in valid_images)
                all_x1 = max(img['bbox'][2] for img in valid_images)
                all_y1 = max(img['bbox'][3] for img in valid_images)

                # Smart boundary adjustment
                page_width = page.rect.width
                page_height = page.rect.height

                # Extend right boundary
                if all_x1 < page_width * 0.8:
                    all_x1 = min(page_width * 0.90, page_width - 10)
                else:
                    all_x1 = min(all_x1 + 40, page_width - 10)

                # Control bottom boundary
                text_blocks = page.get_text("dict")["blocks"]
                max_figure_y = max(img['bbox'][3] for img in valid_images)

                for block in text_blocks:
                    if "lines" in block:
                        block_y0 = block["bbox"][1]
                        if block_y0 > max_figure_y:
                            block_text = ""
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    block_text += span["text"]

                            if any(term in block_text.lower() for term in ["fig.", "figure"]):
                                all_y1 = min(all_y1, block_y0 + 60)
                                break

                # Add margins
                combined_bbox = (
                    max(0, all_x0 - 30),
                    max(0, all_y0 - 50),
                    min(page_width, all_x1),
                    min(page_height, all_y1)
                )

                figure_areas.append({
                    'bbox': combined_bbox,
                    'type': 'combined_architecture_figure',
                    'confidence': 0.9
                })

            return figure_areas[:1]  # Return best area

        except Exception as e:
            print(f"    Figure area detection failed: {e}")
            return []

    def _extract_direct_images(self, doc, paper_id: str, images_dir: str) -> List[str]:
        """Extract images directly from PDF without page screenshots."""
        extracted_images = []

        try:
            print(f"  Starting direct image extraction for {paper_id}...")

            for page_num in range(min(10, len(doc))):  # Check first 10 pages
                page = doc[page_num]
                image_list = page.get_images(full=True)

                if not image_list:
                    continue

                print(f"    Page {page_num + 1}: Found {len(image_list)} images")

                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)

                        # Skip tiny images (likely icons or decorations)
                        min_size = self.image_config.get('min_image_size', [100, 100])
                        if pix.width < min_size[0] or pix.height < min_size[1]:
                            pix = None
                            continue

                        # Skip images that are too large (likely full page scans)
                        if pix.width > 2000 or pix.height > 2000:
                            pix = None
                            continue

                        # Save the image
                        img_filename = f"{paper_id}_page_{page_num+1}_img_{img_index+1}.png"
                        img_path = os.path.join(images_dir, img_filename)

                        pix.save(img_path)
                        extracted_images.append(img_path)

                        print(f"      Saved: {img_filename} ({pix.width}x{pix.height})")

                        pix = None

                        # Limit number of images per page
                        if len(extracted_images) >= 15:  # Max 15 images total
                            break

                    except Exception as e:
                        print(f"      Failed to extract image {img_index + 1}: {e}")
                        continue

                if len(extracted_images) >= 15:
                    break

            return extracted_images

        except Exception as e:
            print(f"    Direct image extraction failed: {e}")
            return []