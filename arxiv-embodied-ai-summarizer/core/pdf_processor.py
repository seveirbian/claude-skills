"""PDF processing module for downloading and extracting images."""

import os
import requests
import fitz  # PyMuPDF
import time
import asyncio
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Optional
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

    async def download_pdf_async(self, session: aiohttp.ClientSession, paper: Dict,
                                output_dir: str, semaphore: asyncio.Semaphore) -> Optional[str]:
        """Download PDF asynchronously from ArXiv with enhanced error handling.

        Args:
            session: aiohttp client session
            paper: Paper metadata dict
            output_dir: Output directory
            semaphore: Semaphore for concurrency control

        Returns:
            Path to downloaded PDF or None if failed
        """
        async with semaphore:  # Control concurrency
            pdf_url = paper['pdf_url']
            filename = f"{paper['id']}.pdf"
            file_path = os.path.join(output_dir, filename)

            if os.path.exists(file_path):
                # Verify existing file is valid
                try:
                    if os.path.getsize(file_path) > 1024:  # At least 1KB
                        print(f"PDF already exists: {filename}")
                        return file_path
                    else:
                        print(f"Existing PDF too small, re-downloading: {filename}")
                        os.remove(file_path)
                except:
                    print(f"Corrupted PDF detected, re-downloading: {filename}")
                    os.remove(file_path)

            # Enhanced headers to avoid blocking
            headers = {
                'User-Agent': self.download_config.get('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'),
                'Accept': 'application/pdf,application/octet-stream,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            timeout = aiohttp.ClientTimeout(
                total=self.download_config.get('timeout', 45),  # Increased timeout
                connect=10,
                sock_read=30
            )
            retry_attempts = self.download_config.get('retry_attempts', 3)
            rate_limit_delay = self.download_config.get('rate_limit_delay', 0.5)

            # Try multiple URL formats if the first fails
            url_variants = [
                pdf_url,
                pdf_url.replace('http://', 'https://'),  # Force HTTPS
                f"https://arxiv.org/pdf/{paper['id']}.pdf",  # Direct arXiv URL
                f"https://export.arxiv.org/pdf/{paper['id']}.pdf"  # Export mirror
            ]

            for attempt in range(retry_attempts):
                for url_idx, current_url in enumerate(url_variants):
                    try:
                        url_info = f" (URL variant {url_idx + 1})" if url_idx > 0 else ""
                        print(f"📥 Downloading PDF: {filename} (attempt {attempt + 1}{url_info})")

                        async with session.get(current_url, headers=headers, timeout=timeout,
                                             allow_redirects=True, max_redirects=5) as response:

                            # Handle different response codes
                            if response.status == 200:
                                # Check content type
                                content_type = response.headers.get('content-type', '').lower()
                                if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                                    if url_idx < len(url_variants) - 1:
                                        continue  # Try next URL variant
                                    else:
                                        raise Exception(f"Invalid content type: {content_type}")

                                # Create temporary file path
                                temp_file_path = f"{file_path}.tmp"

                                # Download with progress tracking
                                total_size = int(response.headers.get('content-length', 0))
                                downloaded_size = 0

                                async with aiofiles.open(temp_file_path, 'wb') as f:
                                    chunk_size = self.download_config.get('chunk_size', 8192)
                                    async for chunk in response.content.iter_chunked(chunk_size):
                                        await f.write(chunk)
                                        downloaded_size += len(chunk)

                                # Verify download completeness
                                if total_size > 0 and downloaded_size < total_size * 0.95:
                                    os.remove(temp_file_path)
                                    raise Exception(f"Incomplete download: {downloaded_size}/{total_size} bytes")

                                # Verify file is not too small (likely error page)
                                if downloaded_size < 10240:  # 10KB minimum
                                    os.remove(temp_file_path)
                                    if url_idx < len(url_variants) - 1:
                                        continue  # Try next URL variant
                                    else:
                                        raise Exception(f"Downloaded file too small: {downloaded_size} bytes")

                                # Rename temp file to final file
                                os.rename(temp_file_path, file_path)

                                print(f"✅ Downloaded: {filename} ({downloaded_size:,} bytes)")

                                # Rate limiting between successful downloads
                                if rate_limit_delay > 0:
                                    await asyncio.sleep(rate_limit_delay)

                                return file_path

                            elif response.status == 429:  # Rate limited
                                print(f"⏱️  Rate limited, waiting longer...")
                                await asyncio.sleep(10)  # Wait 10 seconds for rate limit
                                continue

                            elif response.status in [503, 502, 504]:  # Service unavailable
                                print(f"🔧 Server error {response.status}, trying next variant...")
                                continue

                            else:
                                response.raise_for_status()

                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout downloading {filename} with URL variant {url_idx + 1}")
                        continue
                    except aiohttp.ClientError as e:
                        print(f"🌐 Network error for {filename}: {e}")
                        continue
                    except Exception as e:
                        print(f"❌ Download attempt failed for {filename}: {e}")
                        # Clean up temp file if it exists
                        temp_file_path = f"{file_path}.tmp"
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        continue

                # Wait between retry attempts
                if attempt < retry_attempts - 1:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)

            print(f"❌ All download attempts failed for {filename}")
            return None

    async def download_pdfs_concurrently(self, papers: List[Dict], output_dir: str) -> List[str]:
        """Download multiple PDFs concurrently.

        Args:
            papers: List of paper metadata dicts
            output_dir: Output directory

        Returns:
            List of successful download paths
        """
        if not papers:
            return []

        max_concurrent = self.download_config.get('max_concurrent_downloads', 5)
        semaphore = asyncio.Semaphore(max_concurrent)

        # Use custom connector with connection limits
        connector = aiohttp.TCPConnector(
            limit=max_concurrent * 2,  # Total connection pool size
            limit_per_host=max_concurrent,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
        )

        timeout = aiohttp.ClientTimeout(
            total=self.download_config.get('timeout', 30),
            connect=10  # Connection timeout
        )

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create download tasks
            tasks = [
                self.download_pdf_async(session, paper, output_dir, semaphore)
                for paper in papers
            ]

            print(f"📥 Starting concurrent download of {len(papers)} PDFs (max concurrent: {max_concurrent})")

            # Execute downloads with progress tracking
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            successful_paths = []
            failed_count = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Download failed for {papers[i]['id']}: {result}")
                    failed_count += 1
                elif result is not None:
                    successful_paths.append(result)
                    # Update paper with local path
                    papers[i]['local_pdf_path'] = result
                else:
                    failed_count += 1

            print(f"✅ Download completed: {len(successful_paths)} successful, {failed_count} failed")
            return successful_paths

    def download_pdfs_sync_wrapper(self, papers: List[Dict], output_dir: str) -> List[str]:
        """Synchronous wrapper for async download function.

        Args:
            papers: List of paper metadata dicts
            output_dir: Output directory

        Returns:
            List of successful download paths
        """
        try:
            # Check if we're already in an event loop
            loop = asyncio.get_running_loop()
            # If we're in a loop, run in a thread pool
            with ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self.download_pdfs_concurrently(papers, output_dir))
                )
                return future.result()
        except RuntimeError:
            # No running loop, create a new one
            return asyncio.run(self.download_pdfs_concurrently(papers, output_dir))

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