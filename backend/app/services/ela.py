import base64
import io
from typing import Optional
import numpy as np
from PIL import Image, ImageChops

from app.core.config import settings
from app.schemas.evidence import ELAForensicResult, ELAMetrics


class ELAError(Exception):
    def __init__(self, message: str, error_code: str = "ELA_PROCESSING_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def perform_error_level_analysis(
    image: Image.Image,
    is_png: bool = False,
    quality: Optional[int] = None,
    scale_factor: Optional[float] = None
) -> ELAForensicResult:
    """Perform deterministic Error Level Analysis (ELA) using in-memory JPEG recompression.
    
    ELA computes the absolute pixel difference between an original image and a version
    re-encoded at a standard JPEG quality factor. Areas that have been repeatedly compressed
    or saved at different quality levels exhibit distinct error rates compared to surrounding
    regions.
    
    Important Constraints:
    - ELA is an investigative signal and does NOT prove manipulation, tampering, or AI origin.
    - Uniform areas naturally yield minimal difference. High-frequency textures produce larger differences.
    - For PNG or uncompressed inputs, JPEG recompression error is introduced across the entire canvas.
    """
    recompression_quality = quality or settings.ELA_RECOMPRESSION_QUALITY
    scale = scale_factor or settings.ELA_SCALE_FACTOR
    
    try:
        # Step 1: Normalize color mode to 8-bit per channel RGB
        if image.mode != "RGB":
            # For RGBA or images with transparency, composite onto white background before RGB conversion
            if image.mode in ("RGBA", "LA") or ("transparency" in image.info):
                canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
                canvas.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
                normalized_img = canvas.convert("RGB")
            else:
                normalized_img = image.convert("RGB")
        else:
            normalized_img = image.copy()
        
        # Step 2: In-memory JPEG recompression
        buffer = io.BytesIO()
        normalized_img.save(buffer, format="JPEG", quality=recompression_quality)
        buffer.seek(0)
        recompressed_img = Image.open(buffer)
        recompressed_img.load()
        
        # Step 3: Compute absolute difference
        orig_arr = np.asarray(normalized_img, dtype=np.float32)
        recomp_arr = np.asarray(recompressed_img, dtype=np.float32)
        
        diff_arr = np.abs(orig_arr - recomp_arr)
        
        # Step 4: Numerical summary statistics
        mean_diff = float(np.mean(diff_arr))
        max_diff = float(np.max(diff_arr))
        std_diff = float(np.std(diff_arr))
        
        # Step 5: Visual heatmap scaling and clipping to [0, 255]
        scaled_diff = diff_arr * scale
        heatmap_arr = np.clip(scaled_diff, 0, 255).astype(np.uint8)
        
        heatmap_img = Image.fromarray(heatmap_arr, mode="RGB")
        
        # Step 6: Encode heatmap as PNG into Base64 data URL
        png_buffer = io.BytesIO()
        heatmap_img.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        b64_png = base64.b64encode(png_buffer.getvalue()).decode("ascii")
        data_url = f"data:image/png;base64,{b64_png}"
        
        metrics = ELAMetrics(
            recompression_quality=recompression_quality,
            scale_factor=scale,
            mean_absolute_difference=round(mean_diff, 4),
            max_absolute_difference=round(max_diff, 4),
            std_absolute_difference=round(std_diff, 4)
        )
        
        notes = (
            f"Analyzed with JPEG recompression quality {recompression_quality} and visual scale multiplier {scale}x. "
        )
        if is_png:
            notes += (
                "Input was a lossless PNG; initial lossy JPEG quantization noise was introduced uniformly during analysis. "
            )
        notes += (
            "Higher error brightness highlights regions susceptible to lossy quantization or compression discontinuities; "
            "it is an analytical heuristic and does not prove artificial synthesis or localized editing."
        )
        
        return ELAForensicResult(
            status="SUCCESS",
            metrics=metrics,
            heatmap_data_url=data_url,
            analysis_notes=notes
        )
        
    except Exception as e:
        raise ELAError(f"Error Level Analysis failed during processing: {str(e)}")
