"""
High-Resolution Image Extractor & Converter
===========================================
Extracts genuine illustrations, converts formats to standard JPEG/PNG via sips,
discards unopenable JB2E font masks, and filters out full-page paper sheet scans.
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile

from literature_parser.config.processor_config import (
    FULL_PAGE_MIN_PX,
    MIN_IMAGE_SIZE_BYTES,
)

logger = logging.getLogger(__name__)

# Resolved once at import time; None if sips is not available (non-macOS).
_SIPS = shutil.which("sips") or "/usr/bin/sips"


class ImageManager:
    """Extracts images, converts JP2/TIFF to JPEG/PNG, discards JB2E and full-page background sheets."""

    @staticmethod
    def is_valid_image(path: str) -> bool:
        """Checks if file is a non-empty, valid JPEG or PNG file."""
        if not os.path.exists(path) or os.path.getsize(path) < MIN_IMAGE_SIZE_BYTES:
            return False
        with open(path, "rb") as f:
            header = f.read(16)
            if header.startswith(b"\xff\xd8\xff"):  # JPEG
                return True
            if header.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG
                return True
        return False

    @staticmethod
    def get_image_dimensions(path: str) -> tuple:
        """Gets (width, height) in pixels using macOS sips (graceful fallback on non-macOS)."""
        if not _SIPS or not os.path.exists(_SIPS):
            return 0, 0
        try:
            out = subprocess.check_output(
                [_SIPS, "-g", "pixelWidth", "-g", "pixelHeight", path],
                stderr=subprocess.DEVNULL,
                timeout=15,
            ).decode("utf-8", errors="ignore")
            wm = re.search(r"pixelWidth:\s+(\d+)", out)
            hm = re.search(r"pixelHeight:\s+(\d+)", out)
            if wm and hm:
                return int(wm.group(1)), int(hm.group(1))
        except Exception:
            pass
        return 0, 0

    @classmethod
    def _is_full_page_scan(cls, path: str, is_scanned: bool) -> bool:
        """
        Returns True if the image is a full-page background sheet scan that
        should be discarded (only in scanned mode; pedagogical figures are kept).
        Cover pages (page 1) are never filtered out.
        """
        if not is_scanned:
            return False
        w, h = cls.get_image_dimensions(path)
        if w >= FULL_PAGE_MIN_PX and h >= FULL_PAGE_MIN_PX:
            return True
        return False

    @classmethod
    def extract_pdf_images(
        cls,
        pdf_path: str,
        is_scanned: bool = False,
        target_pages: set = None,
    ) -> list:
        """
        Extracts embedded images from PDF using native PyMuPDF with pdfimages fallback.

        - Converts .jp2/.tiff to high-res JPEG using macOS sips when using CLI.
        - Discards .jb2e font masks.
        - If is_scanned is True, discards full-page background paper sheet scans.
        - Cover art (page 1, sub-index 0) is always kept even in scanned mode.
        """
        # 1. High-speed native PyMuPDF extraction
        try:
            import pymupdf  # type: ignore
            doc = pymupdf.open(pdf_path)
            native_images = []
            for p_idx, page in enumerate(doc):
                p_num = p_idx + 1
                if target_pages and p_num not in target_pages:
                    continue
                imgs = page.get_images(full=True)
                for s_idx, img_info in enumerate(imgs):
                    xref = img_info[0]
                    try:
                        extracted = doc.extract_image(xref)
                        if not extracted:
                            continue
                        img_bytes = extracted.get("image", b"")
                        img_ext = extracted.get("ext", "png").lower()
                        if len(img_bytes) < MIN_IMAGE_SIZE_BYTES:
                            continue
                        if img_ext in ("jb2e", "jbig2"):
                            continue
                        if is_scanned and p_num > 1:
                            w = extracted.get("width", 0)
                            h = extracted.get("height", 0)
                            if w >= FULL_PAGE_MIN_PX and h >= FULL_PAGE_MIN_PX:
                                continue
                        native_images.append({
                            'page': p_num,
                            'sub_idx': s_idx,
                            'ext': img_ext,
                            'data': img_bytes,
                        })
                    except Exception as exc:
                        logger.debug("Failed extracting image xref %d on page %d: %s", xref, p_num, exc)
            doc.close()
            return native_images
        except ImportError:
            pass
        except Exception as e:
            logger.debug("PyMuPDF image extraction failed for '%s': %s, falling back to pdfimages", pdf_path, e)

        # 2. External CLI pdfimages fallback
        raw_images = []
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = ["pdfimages", "-all", "-p"]
            if target_pages and len(target_pages) < 20:
                min_p = min(target_pages)
                max_p = max(target_pages)
                cmd.extend(["-f", str(min_p), "-l", str(max_p)])
            prefix = os.path.join(tmpdir, "img")
            cmd.extend([pdf_path, prefix])

            try:
                subprocess.run(cmd, stderr=subprocess.DEVNULL, check=True, timeout=120)
            except FileNotFoundError:
                logger.warning("pdfimages binary not found; skipping image extraction for '%s'", pdf_path)
                return []
            except subprocess.TimeoutExpired:
                logger.warning("pdfimages timed out (120s) for '%s'", pdf_path)
                return []
            except subprocess.CalledProcessError as e:
                logger.warning("pdfimages failed for '%s' – %s", pdf_path, e)
                return []

            files = sorted(os.listdir(tmpdir))
            for fname in files:
                m = re.match(r"^img-(\d+)-(\d+)\.([a-zA-Z0-9]+)$", fname)
                if not m:
                    continue
                page_num = int(m.group(1))
                if target_pages and page_num not in target_pages:
                    continue
                sub_idx = int(m.group(2))
                raw_ext = m.group(3).lower()
                src_file = os.path.join(tmpdir, fname)

                # 1. Discard unopenable JBIG2 font mask streams (.jb2e)
                if raw_ext in ("jb2e", "jbig2"):
                    continue

                # 2. If JPEG 2000 (.jp2) or TIFF (.tif/.tiff), convert to JPEG using sips
                target_ext = raw_ext
                if raw_ext in ("jp2", "j2k", "tif", "tiff"):
                    if _SIPS and os.path.exists(_SIPS):
                        converted_name = f"conv-{page_num:03d}-{sub_idx:03d}.jpg"
                        converted_path = os.path.join(tmpdir, converted_name)
                        try:
                            res = subprocess.run(
                                [_SIPS, "-s", "format", "jpeg", src_file, "--out", converted_path],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                timeout=15,
                            )
                            if res.returncode == 0 and os.path.exists(converted_path):
                                src_file = converted_path
                                target_ext = "jpg"
                            else:
                                continue
                        except subprocess.TimeoutExpired:
                            logger.warning("sips timed out converting %s", src_file)
                            continue
                    else:
                        continue  # sips not available; skip JP2/TIFF

                # 3. Standardize extensions
                if target_ext == "jpeg":
                    target_ext = "jpg"

                # 4. Filter out zero-size or corrupt images
                if not cls.is_valid_image(src_file):
                    continue

                # 5. Full-page background scan filter for scanned books.
                #    Cover art (page_num==1, sub_idx==0) is always preserved.
                is_cover = page_num == 1 and sub_idx == 0
                if is_scanned and not is_cover and cls._is_full_page_scan(src_file, is_scanned):
                    logger.debug("Discarding full-page scan: page %d sub %d", page_num, sub_idx)
                    continue

                with open(src_file, "rb") as f_in:
                    img_data = f_in.read()

                raw_images.append(
                    {
                        "page": page_num,
                        "sub_idx": sub_idx,
                        "ext": target_ext,
                        "data": img_data,
                    }
                )

        raw_images.sort(key=lambda x: (x["page"], x["sub_idx"]))
        return raw_images
